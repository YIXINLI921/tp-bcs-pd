# taichi environment configuration is requred.
import taichi as ti
import math
ti.init(arch=ti.cpu)
fltype = ti.f64
inttype = ti.i32
# discretisation parameters
nx = 50; ny = 100; mx = 3.015
# time parameter
dt = 1.0; nt = 10000; tt = ti.field(fltype,())
# material parameters
lengthx = 0.36; heighty = 0.72; dx = lengthx / nx; dv = dx**3; delta = dx * mx
emod = 30e6; pr = 0.25; intdee = emod / ((1+pr)*(1-2*pr))
pi = math.pi; bc=12*emod/(pi*delta**4); stabc=bc #6*emod/(pi*(delta**4))/(1-2*pr)
massvec = 0.25*dt*dt*(pi*(delta**2)*dx)*bc/dx*5
## kernel library & field variables
# assign coordinate
coord = ti.Vector.field(2,fltype,(nx,ny))
for ix in range(nx):
    for iy in range(ny):
        coord[ix, iy] = ti.Vector([(0.5 + ix) * dx, (0.5 + iy) * dx], fltype)
# divide the region, devide the subregions
regionint=ti.Vector.field(2,inttype,nx*ny); regionR=ti.Vector.field(2,inttype,nx*ny)
numint = ti.field(inttype,()); numR = ti.field(inttype,())
bcup = ti.Vector.field(2,inttype,nx*ny); bcdown = ti.Vector.field(2,inttype,nx*ny)
bcleft = ti.Vector.field(2,inttype,nx*ny); bcright = ti.Vector.field(2,inttype,nx*ny)
numup = ti.field(inttype,()); numdown = ti.field(inttype,())
numleft = ti.field(inttype,()); numright = ti.field(inttype,())
@ti.kernel
def getsubregions():
    numint[None] = 0; numR[None] = 0; numup[None] = 0; numdown[None] = 0;
    numleft[None] = 0; numright[None] = 0
    # distinguish subregion interior and R
    for ix,iy in coord:
        xi = coord[ix,iy][0]; yi = coord[ix,iy][1]
        if xi > 2 * mx * dx and xi < (lengthx - 2 * mx * dx) and yi > 2 * mx * dx and yi < (heighty - 2 * mx * dx):
            idx = ti.atomic_add(numint[None], 1); regionint[idx] = ti.Vector([ix,iy])
        else: idx = ti.atomic_add(numR[None], 1); regionR[idx] = ti.Vector([ix,iy])
        if yi > (heighty - dx): idx = ti.atomic_add(numup[None], 1); bcup[idx] = ti.Vector([ix,iy])
        if yi < dx: idx = ti.atomic_add(numdown[None], 1); bcdown[idx] = ti.Vector([ix,iy])
        if xi < dx: idx = ti.atomic_add(numleft[None], 1); bcleft[idx] = ti.Vector([ix,iy])
        if xi > (lengthx - dx): idx = ti.atomic_add(numright[None], 1); bcright[idx] = ti.Vector([ix,iy])
# apply norm vectors
normvec = ti.Vector.field(2,fltype,(nx,ny))
@ti.kernel
def getnormvec():
    for i in range(numup[None]):
        ix = bcup[i][0]; iy = bcup[i][1]
        normvec[ix,iy][1] = 1 
    for i in range(numdown[None]):
        ix = bcdown[i][0]; iy = bcdown[i][1]
        normvec[ix,iy][1] = -1
    for i in range(numleft[None]):
        ix = bcleft[i][0]; iy = bcleft[i][1]
        normvec[ix,iy][0] = -1
    for i in range(numright[None]):
        ix = bcright[i][0]; iy = bcright[i][1]
        normvec[ix,iy][0] = 1
# apply offset
numoffset = ti.field(inttype,())
offset = ti.Vector.field(2,inttype,int(2*mx+1)*int(2*mx+1))
@ti.kernel
def offsetkernel():
    numoffset[None] = 0 
    for ix,iy in ti.ndrange((-int(mx),(int(mx)+1)),(-int(mx),(int(mx)+1))):
        if ix==0 and iy==0: continue
        if ti.Vector([ix,iy],inttype).norm() < mx: 
            idx = ti.atomic_add(numoffset[None], 1)
            offset[idx] = [ix,iy]
# compute Lagrangian shape tensor
shapetensor = ti.Matrix.field(2,2,fltype,(nx,ny))
inveshapetensor = ti.Matrix.field(2,2,fltype,(nx,ny))
@ti.func
def dyadicpro(vec1,vec2):
    return ti.Matrix([
        [vec1[0]*vec2[0], vec1[0]*vec2[1]],
        [vec1[1]*vec2[0], vec1[1]*vec2[1]],
        ], fltype)
@ti.kernel
def getshapetensor():
    for ix, iy in shapetensor:
        initensor=ti.Matrix.zero(fltype,2,2); coordi=coord[ix,iy]
        for j in range(numoffset[None]):
            jx=ix+offset[j][0]; jy=iy+offset[j][1]
            if jx<0 or jx>(nx-1) or jy<0 or jy>(ny-1): continue
            coordj = coord[jx,jy]; dcoord = coordj - coordi; dist = dcoord.norm()
            initensor += delta**3/dist**3 * dyadicpro(dcoord,dcoord) * dv
        shapetensor[ix, iy] = initensor
        inveshapetensor[ix,iy] = initensor.inverse()
# apply boundary conditions and body forces
byforce = ti.Vector.field(2,fltype,(nx,ny))
Fext = ti.Vector.field(2,fltype,(nx,ny))
disp = ti.Vector.field(2,fltype,(nx,ny))
@ti.kernel
def getexload():
    for ix,iy in byforce:
        byforce[ix,iy] = ti.Vector([0, 0], fltype)
    for i in range(numup[None]):
        ix = bcup[i][0]; iy = bcup[i][1]
        Fext[ix,iy] = ti.Vector([0.0, -200e3], fltype)
    for i in range(numdown[None]):
        ix = bcdown[i][0]; iy = bcdown[i][1]
        disp[ix,iy] = ti.Vector([0.0, 0.0], fltype)
# get current coordinate
curcoord = ti.Vector.field(2,fltype,(nx,ny))
@ti.kernel
def getcurcoord():
    for ix,iy in curcoord: curcoord[ix,iy] = coord[ix,iy] + disp[ix,iy]
# compute the deformation gradient
defgra = ti.Matrix.field(2,2,fltype,(nx,ny))
@ti.kernel
def getdefgra():
    for ix,iy in defgra:
        intdefgra = ti.Matrix.zero(fltype,2,2); invshapei = inveshapetensor[ix,iy]
        coordi = coord[ix,iy]; curcoordi = curcoord[ix,iy]
        for j in range(numoffset[None]):
            jx = ix + offset[j][0]; jy = iy + offset[j][1]
            if jx<0 or jx>(nx-1) or jy<0 or jy>(ny-1): continue
            coordj = coord[jx,jy]; dcoord = coordj - coordi; dist = dcoord.norm()
            curcoordj = curcoord[jx,jy]; dcurcoord = curcoordj - curcoordi
            intdefgra += delta**3/dist**3 * dyadicpro(dcurcoord,dcoord) * dv
        defgra[ix,iy] = intdefgra @ invshapei
# compute small strain tensor
strain = ti.Matrix.field(2,2,fltype,(nx,ny))
strainold = ti.Matrix.field(2,2,fltype,(nx,ny))
dstrain = ti.Matrix.field(2,2,fltype,(nx,ny))
@ti.kernel
def getstrain():
    for ix,iy in strain:
        strain[ix,iy] = 0.5*(defgra[ix,iy]+defgra[ix,iy].transpose())-ti.Matrix.identity(fltype,2)
        dstrain[ix,iy] = strain[ix,iy] - strainold[ix,iy]; strainold[ix,iy] = strain[ix,iy]
# update Cauchy stress
cauchy = ti.Matrix.field(2,2,fltype,(nx,ny))
pk1 = ti.Matrix.field(2,2,fltype,(nx,ny))
@ti.kernel
def getcauchy():
    for ix,iy in cauchy:
        dstraini = ti.Vector([dstrain[ix,iy][0,0],dstrain[ix,iy][1,1],0,dstrain[ix,iy][1,0],0,0],fltype)
        # constitutive law
        dee = intdee * ti.Matrix([
            [1-pr, pr, pr, 0, 0, 0],
            [pr, 1-pr, pr, 0, 0, 0],
            [pr, pr, 1-pr, 0, 0, 0],
            [0, 0, 0, 1-2*pr, 0, 0],
            [0, 0, 0, 0, 1-2*pr, 0],
            [0, 0, 0, 0, 0, 1-2*pr]
            ],fltype)
        dcauchyi = dee @ dstraini
        cauchy[ix,iy] += ti.Matrix([[dcauchyi[0],dcauchyi[3]], [dcauchyi[3],dcauchyi[1]]],fltype)
        pk1[ix,iy] = cauchy[ix,iy] # small strain
## compute pd force
# original pd force for the internal subregion
pdori = ti.Vector.field(2,fltype,(nx,ny))
@ti.kernel
def getpdori():
    for i in range(numint[None]):
        ix = regionint[i][0]; iy = regionint[i][1]
        pk1i = pk1[ix,iy]; invshapei = inveshapetensor[ix,iy]
        pdorii = ti.Vector.zero(fltype,2)
        for j in range(numoffset[None]):
            jx = ix + offset[j][0]; jy = iy + offset[j][1]
            if jx < 0 or jx > (nx - 1) or jy < 0 or jy > (ny - 1): continue
            pk1j = pk1[jx,jy]; invshapej = inveshapetensor[jx,jy]
            dcoord = coord[jx,jy] - coord[ix,iy]; dist = dcoord.norm()
            pdorii += delta**3/dist**3 * (pk1i @ invshapei + pk1j @ invshapej) @ dcoord * dv
        pdori[ix,iy] = pdorii
    for i in range(numR[None]):
        ix = regionR[i][0]; iy = regionR[i][1]
        pk1i = pk1[ix,iy]; invshapei = inveshapetensor[ix,iy]
        pdorii = ti.Vector.zero(fltype,2)
        for j in range(numoffset[None]):
            jx = ix + offset[j][0]; jy = iy + offset[j][1]
            if jx < 0 or jx > (nx - 1) or jy < 0 or jy > (ny - 1): continue
            pk1j = pk1[jx,jy];dcoord = coord[jx,jy] - coord[ix,iy]; dist = dcoord.norm()
            pdorii += delta**3/dist**3 * (pk1j - pk1i) @ invshapei @ dcoord * dv
        pdori[ix,iy] = pdorii + Fext[ix,iy] / dx - pk1[ix,iy] @ normvec[ix,iy] / dx
# compute correction pd foece eleminating zero-energy mode
pdcor = ti.Vector.field(2,fltype,(nx,ny))
@ti.kernel
def getpdcor():
    for ix,iy in pdcor:
        pdcorii = ti.Vector.zero(fltype,2)
        coordi = coord[ix,iy]; curcoordi = curcoord[ix,iy]; defgrai = defgra[ix,iy]
        for j in range(numoffset[None]):
            jx = ix + offset[j][0]; jy = iy + offset[j][1]
            if jx < 0 or jx > (nx - 1) or jy < 0 or jy > (ny - 1): continue
            coordj = coord[jx,jy];curcoordj = curcoord[jx,jy]; defgraj = defgra[jx,jy]
            dcoordij = coordj - coordi; dcoordji = coordi - coordj; dist = dcoordij.norm()
            dcurcoordij = curcoordj - curcoordi; dcurcoordji = curcoordi - curcoordj
            zedi = dcurcoordij - defgrai @ dcoordij; zedj = dcurcoordji - defgraj @ dcoordji
            Ci = stabc * dyadicpro(dcoordij,dcoordij) / dist**3
            Cj = stabc * dyadicpro(dcoordji,dcoordji) / dist**3
            pdcorii += 0.5 * delta**3/dist**3 * dv * (Ci @ zedi - Cj @ zedj)
        pdcor[ix,iy] = pdcorii
# get summary pd force
pdforce = ti.Vector.field(2,fltype,(nx,ny))
@ti.kernel
def getpdforce():
    for ix,iy in pdforce: pdforce[ix,iy] = pdori[ix,iy] + pdcor[ix,iy]
# time integration
velhalfold = ti.Vector.field(2,fltype,(nx,ny))
velhalf = ti.Vector.field(2,fltype,(nx,ny))
pdforceold = ti.Vector.field(2,fltype,(nx,ny))
vel = ti.Vector.field(2,fltype,(nx,ny))
cn1 = ti.field(fltype, shape=())
cn2 = ti.field(fltype, shape=())
cn = ti.field(fltype, shape=())
@ti.kernel
def getcn12():
    cn1[None] = 0.0; cn2[None] = 0.0
    for ix, iy in disp:
        if ti.abs(velhalfold[ix,iy][0]) > 1e-12:
            ti.atomic_add(cn1[None],
                -disp[ix,iy][0]**2*(pdforce[ix,iy][0]/massvec - pdforceold[ix,iy][0]/massvec)
                /(dt * velhalfold[ix,iy][0])
            )
        if ti.abs(velhalfold[ix,iy][1]) > 1e-12:
            ti.atomic_add(cn1[None],
                -disp[ix,iy][1]**2*(pdforce[ix,iy][1]/massvec - pdforceold[ix,iy][1]/massvec)
                /(dt * velhalfold[ix,iy][1])
            )
        ti.atomic_add(cn2[None],
            disp[ix,iy][0]**2+disp[ix,iy][1]**2)
@ti.kernel
def getcn():
    cn[None] = 0.0
    if ti.abs(cn2[None]) > 1e-12:
        if cn1[None]/cn2[None] > 0.0:
            cn[None] = 2 * ti.sqrt(cn1[None]/cn2[None])
        else: cn[None] = 0
    else: cn[None] = 0
    if cn[None] > 2.0: cn[None] = 1.9
@ti.kernel
def kinematic():
    for ix,iy in disp:
        if tt[None] == 1.0:
            velhalf[ix,iy] = 1 * dt / massvec * (pdforce[ix,iy] + byforce[ix,iy]) / 2
        else:
            velhalf[ix,iy]= ((2.0 - cn[None] * dt) * velhalfold[ix,iy] + 2 * dt / massvec * (pdforce[ix,iy] + byforce[ix,iy])) / (2.0 + cn[None] * dt)
        vel[ix,iy] = 0.5 * (velhalfold[ix,iy] + velhalf[ix,iy])
        disp[ix,iy] += velhalf[ix,iy] * dt
        velhalfold[ix,iy] = velhalf[ix,iy]
        pdforceold[ix,iy] = pdforce[ix,iy]
@ti.kernel
def gettt():
    tt[None] += 1
@ti.kernel
def getoutput():
    print(coord[25,78])
    print(disp[25,78])
    print(pk1[25,78])
# run the taichi
getsubregions()
getnormvec()
offsetkernel()
getshapetensor()
## time integration
for pytt in range(20000):
    # update current time step
    gettt()
    # apply the boundary condition
    getexload()
    # compute current coordinate in the deformed configuration
    getcurcoord()
    # compute the deformation gradient
    getdefgra()
    # compute the small strain tensor
    getstrain()
    # update cauchy stress (including the constitutive law)
    getcauchy()
    # compute pd force
    getpdori(); getpdcor(); getpdforce()
    # time integration
    getcn12(); getcn(); kinematic()
    # reload the boundary condition
    getexload()
getoutput()
