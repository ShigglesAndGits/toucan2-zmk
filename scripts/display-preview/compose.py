import zlib,struct,sys
def pgm(p):
    d=open(p,'rb').read().split(b'\n',3); w,h=map(int,d[1].split()); return w,h,d[3]
files=sys.argv[2:]; imgs=[pgm(f) for f in files]
S=4; gap=12; w,h=imgs[0][0],imgs[0][1]
W=(w*S)*len(imgs)+gap*(len(imgs)+1); Hh=h*S+gap*2
rows=[]
for y in range(Hh):
    row=bytearray([90]*W); yy=(y-gap)//S
    if 0<=y-gap<h*S:
        for k,(_,_,px) in enumerate(imgs):
            x0=gap+k*(w*S+gap)
            for x in range(w): row[x0+x*S:x0+x*S+S]=bytes([px[yy*w+x]])*S
    rows.append(b'\x00'+bytes(row))
c=lambda t,d: struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d))
open(sys.argv[1],'wb').write(b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',W,Hh,8,0,0,0,0))+c(b'IDAT',zlib.compress(b''.join(rows)))+c(b'IEND',b''))
