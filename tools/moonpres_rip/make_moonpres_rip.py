"""make_moonpres_rip.py - the real Moon Presence flip-book from your own rip of the model (see docs/OWNERS_EXTRAS.md).
  python3 pose_moon.py moonp1.bin posed.npy
  python3 make_moonpres_rip.py moonp1.bin posed.npy moonpres.bin
Personal use: the result stays on your card."""
import numpy as np, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbh2view as b
from PIL import Image,ImageDraw,ImageFilter
f=sys.argv[1]; M=b.load(f); idx0=M['idx']; import struct as _st; NB=_st.unpack('<7I',open(f,'rb').read(32)[4:32])[2]      # the bone count is in the file's header
d=open(f,'rb').read(); i=d.rfind(b'LMB1'); a=np.frombuffer(d,'u1',NB,i+8); lm=a[M['v']['b'][:,0]]
Q0=np.load(sys.argv[2])
par=list(range(len(Q0)))
def fd(u):
    while par[u]!=u: par[u]=par[par[u]]; u=par[u]
    return u
for t in idx0:
    a_=fd(t[0]); par[fd(t[1])]=a_; par[fd(t[2])]=a_
roots=np.array([fd(i) for i in range(len(Q0))]); ct={}
for t in idx0: ct[roots[t[0]]]=ct.get(roots[t[0]],0)+1
idx=idx0[np.array([ct[roots[t[0]]]>=60 for t in idx0])]
ztop=Q0[:,2].max()
hair=(lm==0)&(Q0[:,2]>ztop-1.7)
hh=np.clip((Q0[:,2]-(ztop-1.7))/1.7,0,1)
tail=lm>=4
zr=Q0[tail,2]; tz0=Q0[tail,2].max()
FW,FH=224,168; S=(1200,800); y,x=np.mgrid[0:S[1],0:S[0]]
g=(y/S[1])[...,None]; sky=np.array([14,6,22])*(1-g)+np.array([50,12,24])*g
cx,cy,R=600,330,240; dm=np.hypot(x-cx,y-cy)
sky=sky+np.exp(-((dm-R).clip(0)/170)**2)[...,None]*np.array([150,45,20])
disc=np.array([205,95,45])*(0.75+0.25*np.cos(dm/R*1.2))[...,None]
sky=np.where((dm<R)[...,None],disc,sky)
BG=Image.fromarray(sky.clip(0,255).astype('uint8')).convert('RGBA')
zc=(Q0[:,2].min()+Q0[:,2].max())/2
def pose(t):
    X=Q0.copy(); w=2*np.pi*t
    X[hair,1]+=0.42*hh[hair]**1.4*np.sin(w-hh[hair]*3.2)
    X[hair,0]+=0.20*hh[hair]**1.4*np.sin(w+1.3-hh[hair]*3.2)
    dep=np.clip((tz0-X[tail,2])/1.6,0,2)
    ph=(roots[tail]%7)*0.9
    X[tail,1]+=0.20*dep**1.4*np.sin(2*w-dep*2.2+ph)
    X[tail,0]+=0.10*dep**1.4*np.sin(2*w-dep*2.2+ph+1.5)
    arm=(lm==1)|(lm==2); ay=np.abs(Q0[arm,1])
    X[arm,2]+=0.05*(ay/1.6)**1.3*np.sin(w-ay*0.9)
    leg=(lm==3); lz=np.clip((Q0[leg,2].max()-Q0[leg,2])/0.7,0,1); X[leg,1]+=0.025*lz*np.sin(w+0.6)
    body=(lm==0)&~hair; X[body,1]+=0.01*np.sin(w+0.3)
    X[:,2]+=0.03*np.sin(w+0.4); X[:,1]+=0.015*np.sin(w)
    return X
def frame(t):
    X=pose(t); sc=105; px=X[:,1]*sc+cx; py=-(X[:,2]-zc)*sc+cy+30; Z=X[:,0]
    fg=Image.new('RGBA',S,(0,0,0,0)); dr=ImageDraw.Draw(fg)
    A=X[idx[:,1]]-X[idx[:,0]]; B=X[idx[:,2]]-X[idx[:,0]]; N=np.cross(A,B); N/=np.linalg.norm(N,axis=1)[:,None]+1e-9
    for k in np.argsort(-Z[idx].mean(1)):
        tt=idx[k]; rim=(1-abs(N[k,0]))**1.5
        dr.polygon([(px[j],py[j]) for j in tt],fill=(int(8+90*rim),int(2+30*rim),int(12+14*rim),255))
    fg=fg.filter(ImageFilter.GaussianBlur(0.8)); return fg.crop((260,100,940,610)).resize((FW,FH),Image.LANCZOS)

N=32; COLS=8; ROWS=N//COLS
atlas=np.zeros((ROWS*FH,COLS*FW),dtype=np.uint16)
for k in range(N):
    im=np.array(frame(k/N)).astype(np.uint16)
    p=((im[...,0]>>4)<<12)|((im[...,1]>>4)<<8)|((im[...,2]>>4)<<4)|(im[...,3]>>4)
    r,c=divmod(k,COLS); atlas[r*FH:(r+1)*FH,c*FW:(c+1)*FW]=p
import struct
open(sys.argv[3] if len(sys.argv) > 3 else 'moonpres.bin','wb').write(struct.pack('<4I',FW,FH,COLS,N)+atlas.astype('<u2').tobytes())
print('ok',atlas.nbytes)
