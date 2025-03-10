# -*- coding: utf-8 -*-
# testing file from GitHub folder SpinWaveToolkit (as of 2022/06/06)
"""
Created on Tue Aug 25 \n
This module provides analytical tools in Spin wave physics
Available classes are:
    DispersionCharacteristic -- Compute spin wave characteristic in dependance to k-vector \n
    Material -- Class for magnetic materials used in spin wave resreach
    
Available constants: \n
    mu0 -- Magnetic permeability
    
Available functions: \n
    wavenumberToWavelength -- Convert wavelength to wavenumber \n
    wavelengthTowavenumber -- Convert wavenumber to wavelength \n
    
Example code for obtaining propagation lenght and dispersion charactetristic: \n
import SpinWaveToolkit as SWT
import numpy as np
\~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n
#Here is an example of code    \n
import SpinWaveToolkit as SWT \n
import numpy as np \n
kxi = np.linspace(1e-12, 10e6, 150) \n
NiFeChar = SWT.DispersionCharacteristic(kxi = kxi, theta = np.pi/2, phi = np.pi/2,n =  0, d = 10e-9, weff = 2e-6, nT = 1, boundaryCond = 2, Bext = 20e-3, material = SWT.NiFe) \n
DispPy = NiFeChar.GetDispersion()*1e-9/(2*np.pi) #GHz \n
vgPy = NiFeChar.GetGroupVelocity()*1e-3 # km/s \n
lifetimePy = NiFeChar.GetLifetime()*1e9 #ns \n
propLen = NiFeChar.GetPropLen()*1e6 #um \n
\~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n
@author: Ondrej Wojewoda, ondrej.wojewoda@ceitec.vutbr.cz
"""
import numpy as np
from scipy.optimize import fsolve
from numpy import linalg as LA
# from scipy.integrate import trapz

mu0 = 4*np.pi*1e-7; #Magnetic permeability

class DispersionCharacteristic:
    """Compute spin wave characteristic in dependance to k-vector (wavenumber) such as frequency, group velocity, lifetime and propagation length
    #The model uses famous Slavin-Kalinikos equation from https://doi.org/10.1088%2F0022-3719%2F19%2F35%2F014
    Keyword arguments: \n
    kxi -- k-vector (wavenumber) in rad/m, usually vector (default linspace(1e-12, 25e6, 200)) \n
    theta -- out of plane angle in rad, pi/2 is totally inplane magnetization (default pi/2) \n
    phi -- in-plane angle in rad, pi/2 is DE geometry (default pi/2) \n
    n -- the quantization number in z (out-of-plane) direction (default 0) \n
    d -- thickness of layer in m (in z direction) \n
    weff -- effective width of the waveguide in um (optional, default 3e-6 um) \n
    boundaryCond -- 1 is is totally unpinned and 2 is totally pinned boundary condition, 3 is a long wave limit, 4 is partially pinned \n
    dp -- for 4 BC, pinning parameter ranges from 0 to inf. 0 means totally unpinned \n
    aniType -- magnetic anisotropy type, 0 - none (isotropic), 1 - uniaxial, 3 - cubic (not yet implemented). \n
    aniK -- list of anisotropy constants, for aniType=0 is not used, for aniType=1 aniK=[Ku], for aniType=3 aniK=[K1, K2, K3].
    aniDir -- list of directions of anisotropy axes, for uniaxial aniDir=[kappa] (here kappa is an angle from M_0 to the Ku direction in rad)
    
    w0 -- parameter in Slavin-Kalinikos equation in rad*Hz/T w0 = mu0*gamma*Hext \n
    wM -- parameter in Slavin-Kalinikos equation in rad*Hz/T w0 = mu0*gamma*Ms \n
    A -- parameter in Slavin-Kalinikos equation A = Aex*2/(Ms**2*mu0) \n
    
    Availible methods: \n
    GetDisperison \n
    GetLifetime \n
    GetGroupVelocity \n
    GetPropLen \n
    GetPropagationVector \n
    GetPropagationQVector \n
    GetSecondPerturbation \n
    GetDensityOfStates \n
    DemagFactors \n
    Code example: \n
    #Here is an example of code
    kxi = np.linspace(1e-12, 150e6, 150) \n
     \n
    NiFeChar = DispersionCharacteristic(kxi = kxi, theta = np.pi/2, phi = np.pi/2,n =  0, d = 30e-9, weff = 2e-6, nT = 0, boundaryCond = 2, Bext = 20e-3, material = NiFe) \n
    DispPy = NiFeChar.GetDispersion()*1e-9/(2*np.pi) #GHz \n
    vgPy = NiFeChar.GetGroupVelocity()*1e-3 # km/s \n
    lifetimePy = NiFeChar.GetLifetime()*1e9 #ns \n
    propLen = NiFeChar.GetPropLen()*1e6 #um \n
    """
    def __init__(self, Bext, material, d, kxi = np.linspace(1e-12, 25e6, 200), theta = np.pi/2, phi = np.pi/2, weff = 3e-6, boundaryCond = 1, dp=0, aniType=0, aniK=[], aniDir=[]):
        self.kxi = np.array(kxi)
        self.theta = theta
        self.phi= phi
        self.d = d
        self.weff = weff
        self.boundaryCond = boundaryCond
        self.alpha = material.alpha
        #Compute Slavin-Kalinikos parameters wM, w0 A
        self.wM = material.Ms*material.gamma*mu0
        self.w0 = material.gamma*Bext
        self.wU = material.gamma*2*material.Ku/material.Ms
        self.A = material.Aex*2/(material.Ms**2*mu0)
        self.dp = dp
        self.gamma = material.gamma
        self.mu0dH0 = material.mu0dH0
        self.aniType = aniType
        self.aniK = aniK
        self.Ms = material.Ms
        self.aniDir = aniDir
    def GetPropagationVector(self, n = 0, nc = -1, nT = 0):
        """ Gives dimensionless propagation vector \n
        The boundary condition is chosen based on the object property \n
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number
        """
        if nc == -1:
            nc = n
        kxi = np.sqrt(self.kxi**2 + (nT*np.pi/self.weff)**2)
        kappa = n*np.pi/self.d
        kappac = nc*np.pi/self.d
        k = np.sqrt(np.power(kxi,2) + kappa**2)
        kc = np.sqrt(np.power(kxi,2) + kappac**2 )
        # Totally unpinned boundary condition
        if self.boundaryCond == 1:
            Fn = 2/(kxi*self.d)*(1-(-1)**n*np.exp(-kxi*self.d))
            if n == 0 and nc == 0:         
                Pnn = (kxi**2)/(kc**2) - (kxi**4)/(k**2*kc**2)*1/2*((1+(-1)**(n+nc))/2)*Fn
            elif n == 0 and nc != 0 or nc == 0 and n != 0 :
                Pnn =  - (kxi**4)/(k**2*kc**2)*1/np.sqrt(2)*((1+(-1)**(n+nc))/2)*Fn
            elif n == nc:
                Pnn = (kxi**2)/(kc**2) - (kxi**4)/(k**2*kc**2)*((1+(-1)**(n+nc))/2)*Fn
            else:
                Pnn = - (kxi**4)/(k**2*kc**2)*((1+(-1)**(n+nc))/2)*Fn
        # Totally pinned boundary condition
        elif self.boundaryCond == 2:
            if n == nc:
                Pnn = (kxi**2)/(kc**2) + (kxi**2)/(k**2)*(kappa*kappac)/(kc**2)*(1+(-1)**(n+nc)/2)*2/(kxi*self.d)*(1-(-1)**n*np.exp(-kxi*self.d));
            else:
                Pnn = (kxi**2)/(k**2)*(kappa*kappac)/(kc**2)*(1+(-1)**(n+nc)/2)*2/(kxi*self.d)*(1-(-1)**n*np.exp(-kxi*self.d));
        # Totally unpinned condition - long wave limit         
        elif self.boundaryCond == 3:
                if n == 0:
                    Pnn = kxi*self.d/2
                else:
                    Pnn = (kxi*self.d)**2/(n**2*np.pi**2)
        # Partially pinned boundary condition
        elif self.boundaryCond == 4:
            dp = self.dp
            kappa = self.GetPartiallyPinnedKappa(n) #We have to get correct kappa from transversal eq.
            kappac = self.GetPartiallyPinnedKappa(nc)
            if kappa == 0:
                kappa = 1e1
            if kappac == 0:
                kappac = 1e1
            k = np.sqrt(np.power(kxi,2) + kappa**2)
            kc = np.sqrt(np.power(kxi,2) + kappac**2 )
            An = np.sqrt(2*((kappa**2 + dp**2)/kappa**2 + np.sin(kappa*self.d)/(kappa*self.d) * ((kappa**2 - dp**2)/kappa**2*np.cos(kappa*self.d) + 2*dp/kappa*np.sin(kappa*self.d)))**-1)
            Anc = np.sqrt(2*((kappac**2 + dp**2)/kappac**2 + np.sin(kappac*self.d)/(kappac*self.d) * ((kappac**2 - dp**2)/kappac**2*np.cos(kappac*self.d) + 2*dp/kappac*np.sin(kappac*self.d)))**-1)
            Pnnc = kxi*An*Anc/(2*self.d*k**2*kc**2)*((kxi**2 - dp**2)*np.exp(-kxi*self.d)*(np.cos(kappa*self.d) + 
                                                          np.cos(kappac*self.d)) + (kxi - dp)*np.exp(-kxi*self.d)*((dp*kxi - kappa**2)*np.sin(kappa*self.d)/kappa + 
                                                          (dp*kxi - kappac**2)*np.sin(kappac*self.d)/kappac) - (kxi**2 - dp**2)*(1 + np.cos(kappa*self.d)*np.cos(kappac*self.d)) + 
                                                          (kappa**2*kappac**2 - dp**2*kxi**2)*np.sin(kappa*self.d)/kappa*np.sin(kappac*self.d)/kappac - 
                                                          dp*(k**2*np.cos(kappac*self.d)*np.sin(kappa*self.d)/kappa + kc**2*np.cos(kappa*self.d)*np.sin(kappac*self.d)/kappac))
            if n == nc:
                Pnn = kxi**2/kc**2 + Pnnc
            else:
                Pnn = Pnnc
        else:
             raise Exception("Sorry, there is no boundary condition with this number.") 
            
        return(Pnn)
    def GetPropagationQVector(self, n = 0, nc = -1, nT = 0):
        """ Gives dimensionless propagation vector Q \n
        This vector accounts for interaction between odd and even spin wave mode \n
        The boundary condition is chosen based on the object property \n
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number
        """
        if nc == -1:
            nc = n
        kxi = np.sqrt(self.kxi**2 + (nT*np.pi/self.weff)**2)
        kappa = n*np.pi/self.d
        kappac = nc*np.pi/self.d
        if kappa == 0:
            kappa = 1
        if kappac == 0:
            kappac = 1
        k = np.sqrt(np.power(kxi,2) + kappa**2)
        kc = np.sqrt(np.power(kxi,2) + kappac**2 )
        # Totally unpinned boundary condition
        if self.boundaryCond == 1:
            Fn = 2/(kxi*self.d)*(1-(-1)**n*np.exp(-kxi*self.d))
            Qnn = kxi**2/kc**2*(kappac**2/(kappac**2-kappa**2)*2/(kxi*self.d) - kxi**2/(2*k**2)*Fn)*((1-(-1)**(n + nc))/2)
        elif self.boundaryCond == 4:
            dp = self.dp
            kappa = self.GetPartiallyPinnedKappa(n)
            kappac = self.GetPartiallyPinnedKappa(nc)
            if kappa == 0:
                kappa = 1
            if kappac == 0:
                kappac = 1
            An = np.sqrt(2*((kappa**2 + dp**2)/kappa**2 + np.sin(kappa*self.d)/(kappa*self.d) * ((kappa**2 - dp**2)/kappa**2*np.cos(kappa*self.d) + 2*dp/kappa*np.sin(kappa*self.d)))**-1)
            Anc = np.sqrt(2*((kappac**2 + dp**2)/kappac**2 + np.sin(kappac*self.d)/(kappac*self.d) * ((kappac**2 - dp**2)/kappac**2*np.cos(kappac*self.d) + 2*dp/kappac*np.sin(kappac*self.d)))**-1)
            Qnn = kxi*An*Anc/(2*self.d*k**2*kc**2)*((kxi**2-dp**2)*np.exp(-kxi*self.d)*(np.cos(kappa*self.d)-np.cos(kappac*self.d)) + (kxi - dp)*np.exp(-kxi*self.d)*((dp*kxi - 
                            kappa**2)*np.sin(kappa*self.d)/kappa - (dp*kxi - kappac**2)*np.sin(kappac*self.d)/kappac) + (kxi - dp)*((dp*kxi - 
                               kappac**2)*np.cos(kappa*self.d)*np.sin(kappac*self.d)/kappac - (dp*kxi - 
                                 kappa**2)*np.cos(kappac*self.d)*np.sin(kappa*self.d)/kappa) + (1 - 
                                    np.cos(kappac*self.d)*np.cos(kappa*self.d)*2*(kxi**2*dp**2 + 
                                          kappa**2*kappac**2 + (kappac**2 + kappa**2)*(kxi**2 + dp**2))/(kappac**2-kappa**2)
                                            - np.sin(kappa*self.d)*np.sin(kappac**2*self.d)/(kappa*kappac*(kappac**2-kappa**2))*(dp*kxi*(kappa**4+kappac**4) +
                                                 (dp**2*kxi**2 - kappa**2*kappac**2)*(kappa**2 + kappac**2)-2*kappa**2*kappac**2*(dp**2 + kxi**2 - dp*kxi))))
        else:
             raise Exception("Sorry, there is no boundary condition with this number.") 
        return Qnn
#    def GetTVector(self, n, nc, kappan, kappanc):
#        zeta = np.linspace(-self.d/2, self.d/2, 500)
#        An = 1
#        Phin = An*(np.cos(kappan)*(zeta + self.d/2) + self.dp/kappan*np.sin(kappan)*(zeta + self.d/2))
#        Phinc = An*(np.cos(kappanc)*(zeta + self.d/2) + self.dp/kappanc*np.sin(kappanc)*(zeta + self.d/2))
#        Tnn = 1/self.d*trapz(y = Phin*Phinc, x = zeta)
#        return Tnn
    def GetPartiallyPinnedKappa(self, n):
        """ Gives kappa from the transverse equation \n
        Arguments: \n
        n -- Quantization number \n
        """
        def transEq(kappa, d, dp):
            e = (kappa**2 - dp**2)*np.tan(kappa*d) - kappa*dp*2 
            return e
        #The classical thickness mode is given as starting point
        kappa = fsolve(transEq, x0=(n*np.pi/self.d), args = (self.d, self.dp), maxfev=10000, epsfcn=1e-10, factor=0.1)
        return(kappa)
    def GetDispersion(self, n=0, nc=-1, nT=0):
        """ Gives frequencies for defined k (Dispersion relation) \n
        The returned value is in the rad Hz \n
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number """
        if nc == -1:
            nc = n
        if self.boundaryCond == 4:
            kappa = self.GetPartiallyPinnedKappa(n)
        else:
            kappa = n*np.pi/self.d
        kxi = np.sqrt(self.kxi**2 + (nT*np.pi/self.weff)**2)
        k = np.sqrt(np.power(kxi,2) + kappa**2)
        phi = np.arctan((nT*np.pi/self.weff)/self.kxi) - self.phi
        Pnn = self.GetPropagationVector(n = n, nc = nc, nT = nT)
        Fnn = Pnn + np.power(np.sin(self.theta),2)*(1-Pnn*(1+np.power(np.cos(phi),2)) + self.wM*(Pnn*(1 - Pnn)*np.power(np.sin(phi),2))/(self.w0 + self.A*self.wM*np.power(k,2)))
        Na = self.DemagFactors(self.aniType, self.aniK, self.aniDir)
        Fnna = Na[0][0] + Na[1][1] + (Na[0][0]*Na[1][1] + Na[1][1]*np.sin(self.theta)**2-Na[0][1]**2)*self.wM/(self.w0+self.A*self.wM*k**2) +\
               (Na[1][1]*(np.cos(phi)**2-np.sin(self.theta)**2*(1+np.cos(phi)**2))+Na[0][0]*np.sin(phi)**2-Na[1][0]*np.cos(self.theta)*np.sin(2*phi))*Pnn*self.wM/(self.w0+self.A*self.wM*k**2)
        # print("Fnna: ", Fnna)
        # print("Fnn: ", Fnn)
        f = np.sqrt((self.w0 + self.A*self.wM*np.power(k,2))*(self.w0 + self.A*self.wM*np.power(k,2) + self.wM*(Fnn+Fnna)))
        return f
    def DemagFactors(self, aniType=0, aniK=[], aniDir=[]):
        """ Gives calculated demag factors based on selected anisotropy type \n
        (uniaxial, cubic, ...). \n
        Arguments: \n
        aniType -- anisotropy type, 0 - none (isotropic), 1 - uniaxial, 3 - cubic. \n
        aniK -- list of anisotropy constants in J/m3. \n
        Returns: \n
        demTens -- Tensor of demagnetisation factors, 2x2 matrix in the form [[Nxx, Nxy], [Nxy, Nyy]].
        """
        if aniType == 0:
            return np.zeros((2,2))
        elif aniType == 1:
            # Demag factors taken from Lukas Flajsman's PhD thesis, p. 24.
            nxx = -2*aniK[0]/self.Ms**2*np.sin(aniDir[0])**2
            nyy = -2*aniK[0]/self.Ms**2*np.cos(aniDir[0])**2
            return [[nxx, 0],[0, nyy]]
        elif aniType == 3:
            raise Exception("Sorry, cubic anisotropy is not implemented yet!")
        else:
            raise Exception("Sorry, there is no anisotropy with such number.")
    def GetDispersionTacchi(self):
        """ Gives frequencies for defined k (Dispersion relation) \n
        The returned value is in the rad Hz \n
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number """
        ks = np.sqrt(np.power(self.kxi,2))
        phi = self.phi
        wV = np.zeros((6, np.size(ks,0)))
        for idx, k in enumerate(ks):
            Ck = np.array([[-(self.ankTacchi(0, k) + self.CnncTacchi(0, 0, k, phi)), -(self.bTacchi() + self.pnncTachci(0, 0, k, phi)), 0, -self.qnncTacchi(1, 0, k, phi), -self.CnncTacchi(2, 0, k, phi), -self.pnncTachci(2, 0, k, phi)],
                           [(self.bTacchi() + self.pnncTachci(0, 0, k, phi)), (self.ankTacchi(0, k) + self.CnncTacchi(0, 0, k, phi)), -self.qnncTacchi(1, 0, k, phi), 0, self.pnncTachci(2, 0, k, phi), self.CnncTacchi(2, 0, k, phi)],
                           [0, -self.qnncTacchi(0, 1, k, phi), -(self.ankTacchi(1, k) + self.CnncTacchi(1, 1, k, phi)), -(self.bTacchi() + self.pnncTachci(1, 1, k, phi)), 0, -self.qnncTacchi(2, 1, k, phi)],
                           [-self.qnncTacchi(0, 1, k, phi), 0, (self.bTacchi() + self.pnncTachci(1, 1, k, phi)), (self.ankTacchi(1, k) + self.CnncTacchi(1, 1, k, phi)), -self.qnncTacchi(2, 1, k, phi), 0],
                           [-self.CnncTacchi(0, 2, k, phi), -self.pnncTachci(0, 2, k, phi), 0, -self.qnncTacchi(1, 2, k, phi), -(self.ankTacchi(2, k) + self.CnncTacchi(2, 2, k, phi)), -(self.bTacchi() + self.pnncTachci(2, 2, k, phi))],
                           [self.pnncTachci(0, 2, k, phi), self.CnncTacchi(0, 2, k, phi), -self.qnncTacchi(1, 2, k, phi), 0, (self.bTacchi() + self.pnncTachci(2, 2, k, phi)), (self.ankTacchi(2, k) + self.CnncTacchi(2, 2, k, phi))]],
                          dtype=float)
            w, v = LA.eig(Ck)
            wV[:, idx] = np.sort(w)
        return wV
    def CnncTacchi(self, n, nc, k, phi):
        Cnnc = -self.wM/2*(1 - np.sin(phi)**2)*self.PnncTacchi(n,nc,k)
        return Cnnc
    def pnncTachci(self, n, nc, k, phi):
        pnnc = -self.wM/2*(1 + np.sin(phi)**2)*self.PnncTacchi(n,nc,k)
        return pnnc
    def qnncTacchi(self, n, nc, k, phi):
        qnnc = -self.wM/2*np.sin(phi)*self.QnncTacchi(n,nc,k)
        return qnnc
    def OmegankTacchi(self, n, k):
        Omegank = self.w0 + self.wM*self.A*(k**2 + (n*np.pi/self.d)**2)
        return Omegank
    def ankTacchi(self, n, k):
        ank = self.OmegankTacchi(n, k) + self.wM/2 - self.wU/2
        return ank
    def bTacchi(self):
        b = self.wM/2 - self.wU/2
        return b
    def PnncTacchi(self, n, nc,kxi):
        """ Gives dimensionless propagation vector \n
        The boundary condition is chosen based on the object property \n
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number
        """
        kappa = n*np.pi/self.d
        kappac = nc*np.pi/self.d
        k = np.sqrt(np.power(kxi,2) + kappa**2)
        kc = np.sqrt(np.power(kxi,2) + kappac**2 )
        # Totally unpinned boundary condition
        if self.boundaryCond == 1:
            Fn = 2/(kxi*self.d)*(1-(-1)**n*np.exp(-kxi*self.d))
            if n == 0 and nc == 0:         
                Pnn = (kxi**2)/(kc**2) - (kxi**4)/(k**2*kc**2)*1/2*((1+(-1)**(n+nc))/2)*Fn
            elif n == 0 and nc != 0 or nc == 0 and n != 0 :
                Pnn =  - (kxi**4)/(k**2*kc**2)*1/np.sqrt(2)*((1+(-1)**(n+nc))/2)*Fn
            elif n == nc:
                Pnn = (kxi**2)/(kc**2) - (kxi**4)/(k**2*kc**2)*((1+(-1)**(n+nc))/2)*Fn
            else:
                Pnn = - (kxi**4)/(k**2*kc**2)*((1+(-1)**(n+nc))/2)*Fn
        # Totally pinned boundary condition
        elif self.boundaryCond == 2:
            if n == nc:
                Pnn = (kxi**2)/(kc**2) + (kxi**2)/(k**2)*(kappa*kappac)/(kc**2)*(1+(-1)**(n+nc)/2)*2/(kxi*self.d)*(1-(-1)**n*np.exp(-kxi*self.d));
            else:
                Pnn = (kxi**2)/(k**2)*(kappa*kappac)/(kc**2)*(1+(-1)**(n+nc)/2)*2/(kxi*self.d)*(1-(-1)**n*np.exp(-kxi*self.d));
        else:
             raise Exception("Sorry, there is no boundary condition with this number for Tacchi numeric solution.") 
            
        return(Pnn)
    def QnncTacchi(self, n, nc, kxi):
        """ Gives dimensionless propagation vector Q \n
        This vector accounts for interaction between odd and even spin wave mode \n
        The boundary condition is chosen based on the object property \n
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number
        """
        # The totally pinned BC should be added
        kappa = n*np.pi/self.d
        kappac = nc*np.pi/self.d
        if kappa == 0:
            kappa = 1
        if kappac == 0:
            kappac = 1
        k = np.sqrt(np.power(kxi,2) + kappa**2)
        kc = np.sqrt(np.power(kxi,2) + kappac**2 )
        # Totally unpinned boundary condition
        if self.boundaryCond == 1:
            Fn = 2/(kxi*self.d)*(1-(-1)**n*np.exp(-kxi*self.d))
            Qnn = kxi**2/kc**2*(kappac**2/(kappac**2-kappa**2)*2/(kxi*self.d) - kxi**2/(2*k**2)*Fn)*((1-(-1)**(n + nc))/2)
        elif self.boundaryCond == 4:
            dp = self.dp
            kappa = self.GetPartiallyPinnedKappa(n)
            kappac = self.GetPartiallyPinnedKappa(nc)
            if kappa == 0:
                kappa = 1
            if kappac == 0:
                kappac = 1
            An = np.sqrt(2*((kappa**2 + dp**2)/kappa**2 + np.sin(kappa*self.d)/(kappa*self.d) * ((kappa**2 - dp**2)/kappa**2*np.cos(kappa*self.d) + 2*dp/kappa*np.sin(kappa*self.d)))**-1)
            Anc = np.sqrt(2*((kappac**2 + dp**2)/kappac**2 + np.sin(kappac*self.d)/(kappac*self.d) * ((kappac**2 - dp**2)/kappac**2*np.cos(kappac*self.d) + 2*dp/kappac*np.sin(kappac*self.d)))**-1)
            Qnn = kxi*An*Anc/(2*self.d*k**2*kc**2)*((kxi**2-dp**2)*np.exp(-kxi*self.d)*(np.cos(kappa*self.d)-np.cos(kappac*self.d)) + (kxi - dp)*np.exp(-kxi*self.d)*((dp*kxi - 
                            kappa**2)*np.sin(kappa*self.d)/kappa - (dp*kxi - kappac**2)*np.sin(kappac*self.d)/kappac) + (kxi - dp)*((dp*kxi - 
                               kappac**2)*np.cos(kappa*self.d)*np.sin(kappac*self.d)/kappac - (dp*kxi - 
                                 kappa**2)*np.cos(kappac*self.d)*np.sin(kappa*self.d)/kappa) + (1 - 
                                    np.cos(kappac*self.d)*np.cos(kappa*self.d)*2*(kxi**2*dp**2 + 
                                          kappa**2*kappac**2 + (kappac**2 + kappa**2)*(kxi**2 + dp**2))/(kappac**2-kappa**2)
                                            - np.sin(kappa*self.d)*np.sin(kappac**2*self.d)/(kappa*kappac*(kappac**2-kappa**2))*(dp*kxi*(kappa**4+kappac**4) +
                                                 (dp**2*kxi**2 - kappa**2*kappac**2)*(kappa**2 + kappac**2)-2*kappa**2*kappac**2*(dp**2 + kxi**2 - dp*kxi))))
        else:
             raise Exception("Sorry, there is no boundary condition with this number for Tacchi numeric solution.") 
        return Qnn
    
    
#    def GetDispersionNumeric(self, n=0, nc=-1, nT=0):
#        """ Gives frequencies for defined k (Dispersion relation) \n
#        The returned value is in the rad Hz \n
#        Arguments: \n
#        n -- Quantization number \n
#        nc(optional) -- Second quantization number. Used for hybridization \n
#        nT(optional) -- Waveguide (transversal) quantization number """
#        if nc == -1:
#            nc = n
#        if self.boundaryCond == 4:
#            kappa = self.GetPartiallyPinnedKappa(n)
#        else:
#            kappa = n*np.pi/self.d
#        kxi = np.sqrt(self.kxi**2 + (nT*np.pi/self.weff)**2)
#        k = np.sqrt(np.power(kxi,2) + kappa**2)
#        phi = np.arctan((nT*np.pi/self.weff)/self.kxi) - self.phi
#        Pnn = self.GetPropagationVector(n = n, nc = nc, nT = nT)
#        
#        A = np.cos(self.phi)**2 - np.sin(self.theta)**2*(1 - np.cos(self.phi)**2)
#        B = -2*np.cos(self.phi)*np.sin(2*self.theta)
#        C = np.cos(self.theta)*np.sin(self.phi)*np.cos(self.phi)
#        D = -2*np.sin(self.theta)*np.sin(self.phi)
#        E = np.sin(self.phi)**2
#        
#        Fnn = Pnn + np.power(np.sin(self.theta),2)*(1-Pnn*(1+np.power(np.cos(phi),2)) + self.wM*(Pnn*(1 - Pnn)*np.power(np.sin(phi),2))/(self.w0 + self.A*self.wM*np.power(k,2)))
#        f = np.sqrt((self.w0 + self.A*self.wM*np.power(k,2))*(self.w0 + self.A*self.wM*np.power(k,2) + self.wM*Fnn))
#        return f
    def GetGroupVelocity(self, n=0, nc=-1, nT=0):
        """ Gives group velocities for defined k \n
        The group velocity is computed as vg = dw/dk
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number 
        """
        if nc == -1:
            nc = n
        f = self.GetDispersion(n = n, nc = nc, nT = nT)
        vg = np.diff(f)/(self.kxi[2]-self.kxi[1])
        return(vg)
    def GetLifetime(self, n=0, nc=-1, nT=0):
        """ Gives lifetimes for defined k \n
        lifetime is computed as tau = (alpha*w*dw/dw0)^-1
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number """
        if nc == -1:
            nc = n
        w0Ori = self.w0
        self.w0 = w0Ori*0.9999999
        dw0p999 = self.GetDispersion(n = n, nc = nc, nT = nT)
        self.w0 = w0Ori*1.0000001
        dw0p001 = self.GetDispersion(n = n, nc = nc, nT = nT)
        self.w0 = w0Ori
        lifetime = ((self.alpha*self.GetDispersion(n = n, nc = nc, nT = nT) + self.gamma*self.mu0dH0)*(dw0p001 - dw0p999)/(w0Ori*1.0000001 - w0Ori*0.9999999))**-1
        return lifetime
    def GetPropLen(self, n=0, nc=-1, nT=0):
        """ Give propagation lengths for defined k \n
        propagation length is computed as lambda = vg*tau
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number """
        if nc == -1:
            nc = n
        propLen = self.GetLifetime(n = n, nc = nc, nT = nT)[0:-1]*self.GetGroupVelocity(n = n, nc = nc, nT = nT)
        return propLen
    def GetSecondPerturbation(self, n, nc):
        """ Give degenerate dispersion relation based on the secular equation 54 \n
        Arguments: \n
        n -- Quantization number \n
        nc -- Quantization number of crossing mode \n """
        if self.boundaryCond == 4:
            kappa = self.GetPartiallyPinnedKappa(n)
            kappac = self.GetPartiallyPinnedKappa(nc)
        else:
            kappa = n*np.pi/self.d
            kappac = nc*np.pi/self.d
        Om = self.w0 + self.wM*self.A*(kappa**2 + self.kxi**2);
        Omc = self.w0 + self.wM*self.A*(kappac**2 + self.kxi**2);
        Pnnc = self.GetPropagationVector(n = n, nc = nc)
        Pnn = self.GetPropagationVector(n = n, nc = n) 
        Pncnc = self.GetPropagationVector(n = nc, nc = nc)
        Qnnc = self.GetPropagationQVector(n = n, nc = nc)
        wnn = self.GetDispersion(n = n, nc = n)
        wncnc = self.GetDispersion(n = nc, nc = nc)
        if self.theta == 0:
            wdn = np.sqrt(wnn**2+wncnc**2-np.sqrt(wnn**4-2*wnn**2.*wncnc**2+wncnc**4+4*Om*Omc*Pnnc**2*self.wM**2))/np.sqrt(2);
            wdnc = np.sqrt(wnn**2+wncnc**2+np.sqrt(wnn**4-2*wnn**2.*wncnc**2+wncnc**4+4*Om*Omc*Pnnc**2*self.wM**2))/np.sqrt(2);
        elif self.theta == np.pi/2:          
            wdn = (1/np.sqrt(2))*(np.sqrt(wnn**2 + wncnc**2 - 2*Pnnc**2*self.wM**2 - 8*Qnnc**2*self.wM**2 - np.sqrt(wnn**4 + wncnc**4 - 4*(Pnnc**2 + 4*Qnnc**2)*wncnc**2*self.wM**2 - 
                                 2*wnn**2*(wncnc**2 + 2*(Pnnc**2 + 4*Qnnc**2)*self.wM**2) + 4*self.wM**2*(Om*(Pnnc**2 + 4*Qnnc**2)*(2*Omc + self.wM) + self.wM*(Omc*(Pnnc**2 + 
                                           4*Qnnc**2) +  4*(Pncnc + Pnn - 2*Pncnc*Pnn)*Qnnc**2*self.wM + Pnnc**2*(1 - Pnn + Pncnc*(-1 + 2*Pnn) + 16*Qnnc**2)*self.wM))))) 
            wdnc = (1/np.sqrt(2))*(np.sqrt(wnn**2 + wncnc**2 - 2*Pnnc**2*self.wM**2 - 8*Qnnc**2*self.wM**2 + np.sqrt(wnn**4 + wncnc**4 - 4*(Pnnc**2 + 4*Qnnc**2)*wncnc**2*self.wM**2 - 
                                 2*wnn**2*(wncnc**2 + 2*(Pnnc**2 + 4*Qnnc**2)*self.wM**2) + 4*self.wM**2*(Om*(Pnnc**2 + 4*Qnnc**2)*(2*Omc + self.wM) + self.wM*(Omc*(Pnnc**2 + 
                                           4*Qnnc**2) +  4*(Pncnc + Pnn - 2*Pncnc*Pnn)*Qnnc**2*self.wM + Pnnc**2*(1 - Pnn + Pncnc*(-1 + 2*Pnn) + 16*Qnnc**2)*self.wM)))))      
        else:
            raise Exception("Sorry, for degenerate perturbation you have to choose theta = pi/2 or 0.") 
        return(wdn, wdnc)
    def GetDensityOfStates(self, n=0, nc=-1, nT=0):
        """ Give density of states for \n
        Density of states is computed as DoS = 1/vg \n
        Arguments: \n
        n -- Quantization number \n
        nc(optional) -- Second quantization number. Used for hybridization \n
        nT(optional) -- Waveguide (transversal) quantization number """
        if nc == -1:
            nc = n
        DoS = 1/self.GetGroupVelocity(n = n, nc = nc, nT = nT)
        return DoS
    def GetExchangeLen(self):
        exLen = np.sqrt(self.A)
        return exLen
def wavenumberToWavelength(wavenumber):
    """ Convert wavelength to wavenumber
    lambda = 2*pi/k     
    Arguments: \n
    wavenumber -- wavenumber of the wave (rad/m)
    Return: \n
    wavelength (m)"""
    return 2*np.pi/np.array(wavenumber)
def wavelengthTowavenumber(wavelength):
    """ Convert wavenumber to wavelength
    k = 2*pi/lambda 
    Arguments: \n
    wavelength -- wavelength of the wave (m)
    Return: \n
    wavenumber (rad/m)"""
    return 2*np.pi/np.array(wavelength)
      
class Material:
    """Class for magnetic materials used in spin wave resreach \n
    To define custom material please type MyNewMaterial = Material(Ms = MyMS, Aex = MyAex, alpha = MyAlpha, gamma = MyGamma) \n
    Keyword arguments: \n
    Ms -- Saturation magnetization (A/m) \n
    Aex -- Exchange constant (J/m) \n
    alpha -- Gilbert damping ()\n
    gamma -- Gyromagnetic ratio (rad*GHz/T) (default 28.1*pi) \n \n
    Predefined materials are: \n
    NiFe (Permalloy)\n
    CoFeB\n
    FeNi (Metastable iron)"""
    def __init__(self, Ms, Aex, alpha, mu0dH0 = 0, gamma = 28.1*2*np.pi*1e9, Ku = 0):
        self.Ms = Ms
        self.Aex = Aex
        self.alpha = alpha
        self.gamma = gamma
        self.mu0dH0 = mu0dH0
        self.Ku = Ku
#Predefined materials
NiFe = Material(Ms = 800e3, Aex = 16e-12, alpha = 70e-4, gamma = 28.8*2*np.pi*1e9, Ku = 0)
CoFeB = Material(Ms = 1250e3, Aex = 15e-12, alpha = 40e-4, gamma=30*2*np.pi*1e9)
FeNi = Material(Ms = 1410e3, Aex = 11e-12, alpha = 80e-4)
YIG = Material(Ms = 140e3, Aex = 3.6e-12, alpha = 1.5e-4, gamma = 28*2*np.pi*1e9, mu0dH0 = 0.18e-3)
