#%%
"""
https://en.wikipedia.org/wiki/Heat_equation
    especially at subsection "Accounting for radiative loss"
https://en.wikipedia.org/wiki/Finite_difference
https://de.wikipedia.org/wiki/Runge-Kutta-Verfahren

Heat equation:
du/dt = alpha * d²u/dx²

Finite difference:
du/dt = alpha * (u_x+dx,t - 2 u_x,t + u_x-dx,t) / (dx²)

RungeKutta: 
k1 = dudt(u,                          t        )
k2 = dudt(u + dt/2 * k1,              t + dt/2 )
k3 = dudt(u - dt * k1 + 2 * dt * k2,  t + dt   )
u_t+dt = u_t + dt * (1/6 * k1 + 4/6 * k2 + 1/6 * k3)
"""


#%%
import numpy as np
import matplotlib.pyplot as plt

#%%


# https://www.toppr.com/ask/question/the-average-thermal-conductivity-of-the-walls-including-the-windows-and-roof-of-the-house/
# Wall thickness = 21cm
# Thermal conductivity: 0.48 W/m°K
# https://medium.com/@piotrgoawski/comparison-of-thermal-insulation-for-external-walls-8444ec6a7234)
# Styrofoam:   0.044 W/m°K
# Polystyrene: 0.031 W/m°K

Distance = 0.5 # [m]
Time = 5 * 60 * 60 # [s]
wallThickness = 0.21
insulationThickness = 0.10

timeSteps = 1000000
spaceSteps = 100


dx = Distance / spaceSteps
dt = Time / timeSteps
xs = np.arange(0, Distance, dx)
ts = np.arange(0, Time, dt)

tRoom = 20 + 273 # [°K]
def tOutside(time):   #  = 10 + 273 # [°K]
    return 0 + 273
    # amplitude = 2.5
    # meanTemp = 10 + 273
    # cyclesPerSecond = 2.0 * np.pi / (24 * 60 * 60)
    # return amplitude * np.sin(time * cyclesPerSecond) + meanTemp

fullWallThickness   = wallThickness + insulationThickness
spaceStepsPerMeter  = spaceSteps / Distance
wallStartMeter       = (Distance / 2) - (fullWallThickness / 2)
wallEndMeter         = wallStartMeter + wallThickness
insulationStartMeter = wallEndMeter
insulationEndMeter   = (Distance / 2) + (fullWallThickness / 2)
wallStart       = int(wallStartMeter       * spaceStepsPerMeter)
wallEnd         = int(wallEndMeter         * spaceStepsPerMeter)
insulationStart = int(insulationStartMeter * spaceStepsPerMeter)
insulationEnd   = int(insulationEndMeter   * spaceStepsPerMeter)


temp0 = np.zeros((spaceSteps))
temp0[:wallStart] = tRoom
temp0[wallStart:insulationEnd] = np.linspace(tRoom, tOutside(0), insulationEnd - wallStart)
temp0[insulationEnd:] = tOutside(0)


# constants
thermalConductivityAir       = 0.026  # W / m °K
thermalConductivityWater     = 0.609
thermalConductivityConcrete  = 0.92
thermalConductivityStyrofoam = 0.044
densityAir       = 1.2   # kg / m^3   (assumes room temperature)
densityConcrete  = 2400
densityStyrofoam = 950
specHeatCapacityAir       = 1000   # J / kg °K
specHeatCapacityWater     = 4184
specHeatCapacityConcrete  = 1000
specHeatCapacityStyrofoam = 1340
emissivityConcrete = 0.9
sBoltzmann = 5.670e-8     # W / m^2 K^4

# alpha: thermal diffusivity
# alpha = k / c / p
# k: thermal conductivity
# p: density
# c: specific heat capacity
alpha                                = np.zeros((spaceSteps))
alphaAir                             = thermalConductivityAir / (densityAir * specHeatCapacityAir)
alphaWall                            = thermalConductivityConcrete / (densityConcrete * specHeatCapacityConcrete)
alphaInsulation                      = thermalConductivityStyrofoam / (densityStyrofoam * specHeatCapacityStyrofoam)
alpha[:wallStart]                    = alphaAir
alpha[wallStart:wallEnd]             = alphaWall
alpha[insulationStart:insulationEnd] = alphaInsulation
alpha[insulationEnd:]                = alphaAir

# beta: radiative loss
# only at wall's outer surface (but maybe also in air?)
# beta = mu / c / p
# mu: depends on S.Boltzmann and emissivity
beta = np.zeros((spaceSteps))
betaWallSurface = emissivityConcrete * sBoltzmann / (densityConcrete * specHeatCapacityConcrete * dx)
beta[insulationEnd] = betaWallSurface


def dTempdt(tempBefore, time):
    
    tempShiftR      = np.zeros(tempBefore.shape)
    tempShiftR[1:]  = tempBefore[:-1]
    tempShiftR[0]   = tRoom

    tempShiftL      = np.zeros(tempBefore.shape)
    tempShiftL[:-1] = tempBefore[1:]
    tempShiftL[-1]  = tOutside(time)

    dTdt = alpha * (tempShiftL - 2 * tempBefore + tempShiftR) / (dx**2)

    # accounting for radiation @TODO: how about *in*coming radiation? Probably stronger than outgoing.
    dTdt -= beta * np.power(tempBefore, 4)

    return dTdt


print(f"alpha air: {alphaAir}")
print(f"alpha concrete: {alphaWall}")
print(f"alpha insulation: {alphaInsulation}")
print(f"beta wall: {betaWallSurface}")

#%%
temps = [temp0]
for step in range(1, timeSteps):
    if step % 100 == 0:
        print(step / timeSteps)
    
    time = step * dt
    tempLast = temps[step-1]

    # Runge Kutta 2
    k1 = dTempdt(tempLast,                  time            )
    k2 = dTempdt(tempLast + 0.5 * dt * k1,  time + 0.5 * dt )
    delta = 0.5 * k1 + 0.5 * k2

    # Runge Kutta 3
    # k1 = dTempdt(tempLast,                          time            )
    # k2 = dTempdt(tempLast + 0.5 * dt * k1,          time + 0.5 * dt )
    # k3 = dTempdt(tempLast - dt * k1 + 2 * dt * k2,  time + dt       )
    # delta = (1.0/6.0) * k1 + (4.0/6.0) * k2 + (1.0 / 6.0) * k3

    tempNew = tempLast + dt * delta
    
    temps.append(tempNew)




# %%
plt.plot(xs, temps[0] - 273, label="t=0")
plt.plot(xs, temps[1000] - 273, label="t=1000")
plt.plot(xs, temps[10000] - 273, label="t=10000")
plt.plot(xs, temps[100000] - 273, label="t=100000")
plt.axvline(x = wallStart * dx)
plt.axvline(x = wallEnd *dx)
plt.axvline(x = insulationEnd *dx)
plt.legend()

# %%
from matplotlib.animation import FuncAnimation


fig, ax = plt.subplots()
ln, = ax.plot(xs, temps[0] - 273)
ax.axvline(x = wallStart * dx)
ax.axvline(x = wallEnd * dx)
ax.axvline(x = insulationEnd * dx)

def init():
    return ln,

def update(frame):
    print(frame / timeSteps)
    ln.set_data(xs, temps[frame] - 273)
    return ln,

ani = FuncAnimation(fig, update, init_func=init, blit=True, frames=np.arange(0, timeSteps, 10000))
ani.save("movie.gif")
plt.show()

# %%
hours = ts / 60 / 60
tWallInside  = [temp[wallStart] - 273 for temp in temps]
tWallOutside = [temp[insulationEnd] - 273 for temp in temps]
deltaT = np.round(tWallInside[-1] - (tRoom-273), 2)
plt.plot(hours[:-1], tWallInside, label="T_{inside}",   color=(0.5, 0.125, 0.125))
plt.plot(hours[:-1], tWallOutside, label="T_{outside}", color=(0.125, 0.125, 0.5))
plt.xlabel("time [h]")
plt.ylabel("temperature [°C]")
plt.suptitle(f"Conductivity = {thermalConductivityConcrete} over {wallThickness}m\n Conductivity = {thermalConductivityStyrofoam} over {insulationThickness}m\n\delta T = {deltaT}")
plt.legend()

# %%
# deltaT = np.round(tWallInside[-1] - (tRoom-273), 2)
# plt.plot(hours[:-1], tWallInside, label="cond 0.05")
# plt.plot(hours[:-1], tWallInside1, label="cond 0.1")
# plt.plot(hours[:-1], tWallInside0, label="cond 0.92")
# plt.xlabel("time [h]")
# plt.ylabel("temperature [°C]")
# plt.suptitle("Temperature wall inside")
# plt.legend()
# %%
