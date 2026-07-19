from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

ROOT = Path(__file__).parent
engine = create_engine(f"sqlite:///{ROOT / 'route53.db'}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase): pass

class HostedZone(Base):
    __tablename__ = "hosted_zones"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    private_zone: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    records: Mapped[list["DnsRecord"]] = relationship(back_populates="zone", cascade="all, delete-orphan")

class DnsRecord(Base):
    __tablename__ = "dns_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    zone_id: Mapped[str] = mapped_column(ForeignKey("hosted_zones.id"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    ttl: Mapped[int] = mapped_column(Integer, default=300)
    routing_policy: Mapped[str] = mapped_column(String, default="Simple")
    zone: Mapped[HostedZone] = relationship(back_populates="records")

class Login(BaseModel): email: str
class ZoneInput(BaseModel):
    name: str = Field(min_length=1)
    comment: str = ""
    private_zone: bool = False
class RecordInput(BaseModel):
    name: str = Field(min_length=1)
    type: str
    value: str = Field(min_length=1)
    ttl: int = Field(default=300, ge=0)
    routing_policy: str = "Simple"

def db():
    with SessionLocal() as session: yield session

def user(request: Request):
    email = request.cookies.get("route53_user")
    if not email: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    return {"email": email}

def zone_out(z: HostedZone):
    return {"id":z.id,"name":z.name,"comment":z.comment,"private_zone":bool(z.private_zone),"created_at":z.created_at,"record_count":len(z.records)}
def record_out(r: DnsRecord):
    return {"id":r.id,"zone_id":r.zone_id,"name":r.name,"type":r.type,"value":r.value,"ttl":r.ttl,"routing_policy":r.routing_policy}

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title="Route 53 Clone API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://34.87.172.133:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health(): return {"ok": True}
@app.post("/api/auth/login")
def login(body: Login, response: Response):
    response.set_cookie("route53_user", body.email, httponly=True, samesite="lax")
    return {"email":body.email}
@app.post("/api/auth/logout")
def logout(response: Response): response.delete_cookie("route53_user"); return {"ok":True}
@app.get("/api/auth/me")
def me(current=Depends(user)): return current

@app.get("/api/zones")
def list_zones(q: str = "", offset: int = 0, limit: int = 20, _: dict = Depends(user), session: Session = Depends(db)):
    rows = session.scalars(select(HostedZone).where(HostedZone.name.contains(q)).order_by(HostedZone.name).offset(offset).limit(limit)).all()
    return [zone_out(x) for x in rows]
@app.post("/api/zones", status_code=201)
def create_zone(body: ZoneInput, _: dict = Depends(user), session: Session = Depends(db)):
    name = body.name.rstrip(".") + "."
    if session.scalar(select(HostedZone).where(HostedZone.name == name)): raise HTTPException(409, "A hosted zone with that name already exists")
    z=HostedZone(name=name, comment=body.comment, private_zone=int(body.private_zone)); session.add(z); session.commit(); session.refresh(z); return zone_out(z)
@app.get("/api/zones/{zone_id}")
def get_zone(zone_id: str, _: dict = Depends(user), session: Session = Depends(db)):
    z=session.get(HostedZone, zone_id)
    if not z: raise HTTPException(404, "Hosted zone not found")
    return zone_out(z)
@app.put("/api/zones/{zone_id}")
def update_zone(zone_id: str, body: ZoneInput, _: dict = Depends(user), session: Session = Depends(db)):
    z=session.get(HostedZone, zone_id)
    if not z: raise HTTPException(404, "Hosted zone not found")
    z.name=body.name.rstrip(".")+"."; z.comment=body.comment; z.private_zone=int(body.private_zone); session.commit(); session.refresh(z); return zone_out(z)
@app.delete("/api/zones/{zone_id}", status_code=204)
def delete_zone(zone_id: str, _: dict = Depends(user), session: Session = Depends(db)):
    z=session.get(HostedZone, zone_id)
    if not z: raise HTTPException(404, "Hosted zone not found")
    session.delete(z); session.commit()

@app.get("/api/zones/{zone_id}/records")
def list_records(zone_id: str, q: str = "", type: Optional[str] = None, _: dict = Depends(user), session: Session = Depends(db)):
    if not session.get(HostedZone, zone_id): raise HTTPException(404, "Hosted zone not found")
    query=select(DnsRecord).where(DnsRecord.zone_id==zone_id, DnsRecord.name.contains(q))
    if type: query=query.where(DnsRecord.type==type)
    return [record_out(x) for x in session.scalars(query.order_by(DnsRecord.name)).all()]
@app.post("/api/zones/{zone_id}/records", status_code=201)
def create_record(zone_id: str, body: RecordInput, _: dict = Depends(user), session: Session = Depends(db)):
    if not session.get(HostedZone, zone_id): raise HTTPException(404, "Hosted zone not found")
    r=DnsRecord(zone_id=zone_id, **body.model_dump()); session.add(r); session.commit(); session.refresh(r); return record_out(r)
@app.put("/api/records/{record_id}")
def update_record(record_id: str, body: RecordInput, _: dict = Depends(user), session: Session = Depends(db)):
    r=session.get(DnsRecord,record_id)
    if not r: raise HTTPException(404,"Record not found")
    for k,v in body.model_dump().items(): setattr(r,k,v)
    session.commit(); session.refresh(r); return record_out(r)
@app.delete("/api/records/{record_id}", status_code=204)
def delete_record(record_id: str, _: dict = Depends(user), session: Session = Depends(db)):
    r=session.get(DnsRecord,record_id)
    if not r: raise HTTPException(404,"Record not found")
    session.delete(r); session.commit()
