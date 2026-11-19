import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbh2view as b, numpy as np
from PIL import Image,ImageDraw,ImageFilter
import sys, struct; f=sys.argv[1]; NBc=struct.unpack('<7I',open(f,'rb').read(32)[4:32])[2]      # the bone count is in the file's header
d=open(f,'rb').read(); i=d.rfind(b'LMB1'); a=np.frombuffer(d,'u1',NBc,i+8)
M=b.load(f); P=b.skin(M,M['an']['Idle'][1][0],NBc); lm=a[M['v']['b'][:,0]]
def rot_to(v,t):
    v=v/np.linalg.norm(v); t=t/np.linalg.norm(t); k=np.cross(v,t); s=np.linalg.norm(k); c=v@t
    if s<1e-6: return np.eye(3)
    k/=s; K=np.array([[0,-k[2],k[1]],[k[2],0,-k[0]],[-k[1],k[0],0]]); th=np.arctan2(s,c)
    return np.eye(3)+np.sin(th)*K+(1-np.cos(th))*K@K
Q=P.copy(); C=np.array([0,0,0.9])
for L in range(1,13):
    m=lm==L
    if not m.any(): continue
    if L==3:
        for sg in (1,-1):
            mm=m&((P[:,1]>=0) if sg>0 else (P[:,1]<0)); pp=P[mm]
            if not len(pp): continue
            rt=pp[np.argmax(pp[:,2])]; tp=pp[np.argmin(pp[:,2])]; vv=pp-rt
            R=rot_to(tp-rt,np.array([0,sg*0.08,-1.0])); Q[mm]=rt+vv@R.T
        continue
    pts=P[m]; root=pts[np.argmin(np.linalg.norm(pts-C,axis=1))]
    v=pts-root; mean=v.mean(0)
    if L in (1,2):
        sg=1 if pts[:,1].mean()>0 else -1; tgt=np.array([0,sg,0.08]); sc=2.2
    elif L==3:
        tgt=np.array([0,0,-1.0]); sc=1.0
    else:
        sg=1 if root[1]>0.02 else (-1 if root[1]<-0.02 else (1 if L%2 else -1)); tgt=np.array([0.0,sg*(0.12+0.05*(L%4)),-1.0]); sc=1.0
    R=rot_to(mean,tgt); w=(v@R.T)*sc
    if L>=4:
        tip=w[np.argmax(np.linalg.norm(w,axis=1))]; sg2=1 if tip[1]>=0 else -1
        w=w*0.6; w[:,1]=sg2*np.abs(w[:,2])*(0.05+0.035*(L%5)); root=np.array([root[0]*0.3,root[1]*0.3,root[2]])
    if L>=4:
        zb=np.round(w[:,2]/0.08).astype(int); 
        for z in np.unique(zb):
            mk=zb==z; c=w[mk].mean(0); dd=w[mk]-c; dd[:,2]=0; n_=np.linalg.norm(dd,axis=1,keepdims=True); dd=np.where(n_>1e-5,dd/np.maximum(n_,1e-9)*0.05,0); ww=w[mk]; ww[:,0]=c[0]+dd[:,0]; ww[:,1]=c[1]+dd[:,1]; w[mk]=ww
    Q[m]=root+w
np.save(sys.argv[2],Q); sys.exit()
idx=M['idx']
def draw(Qp,S,yaw,scale,ox,oy):
    c,s=np.cos(yaw),np.sin(yaw); R=np.array([[c,-s,0],[s,c,0],[0,0,1]]); X=Qp@R.T
    px=X[:,1]*scale+ox; py=-X[:,2]*scale+oy; Z=X[:,0]
    im=Image.new('RGBA',(S[0],S[1]),(0,0,0,0)); dr=ImageDraw.Draw(im)
    A=X[idx[:,1]]-X[idx[:,0]]; B=X[idx[:,2]]-X[idx[:,0]]; N=np.cross(A,B); N/=np.linalg.norm(N,axis=1)[:,None]+1e-9
    for k in np.argsort(-Z[idx].mean(1)):
        t=idx[k]; rim=1-abs(N[k,0]); col=(int(10+70*rim**2),int(3+22*rim**2),int(14+20*rim**2),255)
        dr.polygon([(px[j],py[j]) for j in t],fill=col)
    return im
for nm,Qp in (('idle',P),('posed',Q)):
    for yaw in (0,3.1416):
        draw(Qp,(500,500),yaw,70,250,330).convert('RGB').save(f'./{nm}_{int(yaw)}.png')
