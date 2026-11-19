import struct,sys,numpy as np
from PIL import Image,ImageDraw
def load(f):
    d=open(f,'rb').read(); nV,nI,NB,nA,nAt,nS,nT=struct.unpack_from('<7I',d,4); o=32
    for t in range(nT):
        l=d[o]; o+=1+l; w,h=struct.unpack_from('<HH',d,o); o+=4+w*h*4
    o+=nS*12
    v=np.frombuffer(d,dtype=[('p','<3f4'),('uv','<2f4'),('b','u1',4)],count=nV,offset=o); o+=nV*24
    idx=np.frombuffer(d,'<u2',nI,o).reshape(-1,3); o+=nI*2; o+=16*nAt
    an={}
    for a in range(nA):
        nm=d[o:o+32].split(b'\0')[0].decode(); fps,nf,tx,ty=struct.unpack_from('<fIff',d,o+32); o+=48
        fr=np.frombuffer(d,'<f4',nf*(NB+nAt)*12,o).reshape(nf,NB+nAt,12); o+=nf*(NB+nAt)*12*4; an[nm]=(fps,fr)
    return dict(NB=NB,v=v,idx=idx,an=an)
def skin(M,frame,NB):
    P=M['v']['p'].astype(float); b0=M['v']['b'][:,0].astype(int); b1=M['v']['b'][:,1].astype(int); w=(M['v']['b'][:,2]/255.0)[:,None]
    F=frame[:NB].reshape(NB,3,4); h=np.c_[P,np.ones(len(P))]
    return w*np.einsum('vij,vj->vi',F[b0],h)+(1-w)*np.einsum('vij,vj->vi',F[b1],h)
def render(P,idx,col,yaw,S=420,box=None):
    c,s=np.cos(yaw),np.sin(yaw); R=np.array([[c,-s,0],[s,c,0],[0,0,1]]); Q=P@R.T
    X=Q[:,1];Y=-Q[:,2];Z=Q[:,0]
    if box is None: box=(X.min(),X.max(),Y.min(),Y.max())
    x0,x1,y0,y1=box; sc=S*0.95/max(x1-x0,y1-y0)
    im=Image.new('RGB',(S,S),(20,20,30)); dr=ImageDraw.Draw(im)
    tri=idx; dep=Z[tri].mean(1); order=np.argsort(-dep)
    A=Q[tri[:,1]]-Q[tri[:,0]]; B=Q[tri[:,2]]-Q[tri[:,0]]; N=np.cross(A,B); N/=np.linalg.norm(N,axis=1)[:,None]+1e-9
    for k in order:
        t=tri[k]; sh=0.45+0.55*abs(N[k,0]*0.3+N[k,2]*0.5+N[k,1]*0.4)
        c0=col[t[0]]; fc=tuple(int(min(255,x*sh)) for x in c0)
        dr.polygon([((X[i]-x0)*sc+10,(Y[i]-y0)*sc+10) for i in t],fill=fc)
    return im
