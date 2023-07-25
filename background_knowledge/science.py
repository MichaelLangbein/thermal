#%%
import numpy as np


"""
|name                 |Formula                 |Unit         |      Notes                                                           |
|---------------------|------------------------|-------------|----------------------------------------------------------------------|
|Energy               |Q                       |[J]          |                                                                      |
|Flux                 |F = dQ/dt               |[w]          |                                                                      |
|Irradiance           |E = F/A                 |[W/m^2]      |  Flux arriving at receiver-surface. E = rho T⁴ by Boltzmann's law.   |
|                     |                        |             |  Think of *ir*radiance as *integrated* radiance                      |
|Monochr. irradiance: |Elambda = dE/dlambda    |[W/m^3]      |  E_lambda = B * PI for equally distributed radiance                  |
|Radiance             |B = dElambda / domega   |[W/m^3 angle]|  Planck's law: B(lambda, T)                                          |
"""


k   = 1.381e-23   # Boltzmann  [J/K]
h   = 6.626e-34   # Planck     [Js]
c   = 2.998e8     # lightspeed [m/s]
rho = 5.670e-8    # S.Bolzmann [W/(m²K⁴)]


"""
UV
VIS
IR: NIR, thermal
Micro
Radio
"""

# Top: high wavelength, low energy
lambda_radio_start = 1000000
lambda_radio_end   = 1  # [m]
lambda_micro_start = lambda_radio_end
lambda_micro_end   = 1e-3
lambda_ir_start    = lambda_micro_end
lambda_ir_end      = 0.75e-6
lambda_vis_start   = lambda_ir_end
lambda_vis_end     = 0.38e-6
lambda_uv_start    = lambda_vis_end
lambda_uv_end      = 10e-9
# Bottom: low wavelength, high energy


def wave_energy(wavelength):
    energy = h * c / wavelength  # [J]
    return energy


def black_body_radiance(wavelength, temperature):
    """
        Planck's law: https://en.wikipedia.org/wiki/Planck%27s_law
        wavelength: [meter]
        temperature: [°Kelvin]
    """
    factor = (2.0 * h * c**2) / (wavelength**5)
    exponent = (h * c) / (wavelength * k * temperature)
    radiance =  factor / (np.exp(exponent) - 1)
    return radiance


def black_body_temperature(wavelength, radiance):
    """
        Planck's law, solved for T
        wavelength: [meter]
        radiance: [W/m³ angle]
    """
    factor = (h * c) / k
    loged = (2 * h * c**2) / (wavelength**5 * radiance)
    return factor / (wavelength * np.log(loged + 1))



def black_body_most_intense_wavelength(temperature):
    """
        Wien's law:
        dB/dlambda = 0 -> lambda_max = 0.002898 [meter*Kelvin] /T
    """
    return 0.002898 / temperature


def black_body_irradiance(temperature):
    """
        Boltzmann's law:
        E = int_0^infty pi * I(lambda, T) dlambda = rho * T^4
    """
    return rho * np.power(temperature, 4)



# Facts about thermal:
# - can be taken by day and night (because it's being emmited, not reflected)
# - atmosphere aborbs some thermal, so only a few specific bands can be measured
# - but atmospheric *scattering* is minimal, so need not account for that
# - thermal sensors are cooled to close to absolute zero, so they don't radiate themselves
# - thermal resolution is often worse than optical, because waves have less energy
# - mirrors reflect lots of visible light, but not much thermal
# - Aluminum foil reflects thermal (emissivity: 0.08). You can place such foil behind your radiator
# - Snow does, too: that's why it doesn't melt until long in the summer (it also reflects visible, which is why it's white)
# - Stainless steel does, too (emissivity: 0.16).
# - Distilled water doesnt: emissivity 0.99. In fact, water absorbs almost all incident energy and reflects very little. Thus its high emissivity.
# - Thermal does not go through glass, but easily through plastic. Alluminum is a very good IR reflector: https://www.youtube.com/watch?v=baJtBDJDQDQ
# - 
# For now my suspicion is that there is no material on the outside of buildings that reflects heat very strongly... so we can ignore this for now.
#
# https://www.isprs.org/proceedings/xxxiii/congress/part1/239_xxxiii-part1.pdf
# - 3-35 micro-meter is commonly called TIR
# - 8-14 micro-meter is barely absorbed in atmosphere
#     - especially 10-12 is good, because avoids ozone-absorption peak at 9.6
#     - below 10 absorbed by water vapor, above 12 absorbed by CO2
# - 3-5 and 17-25 are still ok
# - but 3-5 overlaps with solar reflection during day and 17-25 is not well investigated
# - pre-dawn pictures are preferred, because minimal effect of solar heating
# - pretty hard to co-register thermal, because of its poor resolution

# https://eo4society.esa.int/wp-content/uploads/2021/04/2017Land_D2T3-P_Cartalis_Thermal.pdf
# - only radiative heat-transfer travels through space, so satellites can only observe that. We can ignore convection and conduction.
# - thermal capacity c [cal / gram / °C]: ability of material to store heat. meassured as calories to heat one gram by one degree.
# - thermal conductivity K [cal / cm / sec]: rate of heat transfer. meassured as calories passing through 1cm distance in a second between two surfaces with 1°C difference
# - thermal intertia P [cal / cm² / sqrt(sec) / °C]: P = sqrt(K * c * density)
# - NIR & SWIR behaves almost like VIS in that it is mostly reflected sunlight
# - TIR is heat energy which is not reflected (except on aluminum), but radiated because of objects' own heat
# - Forrest fires are very hot, so their dominant wavelength is low and NIR or SWIR are appropriate bands
# - Ambient buildings are not, so TIR is a better band
# - Distilled water: emissivity 0.99. In fact, water absorbs almost all incident energy and reflects very little. Thus its high emissivity.
# - Sheet metal roofs reflect a lot and absorb little. Thus, metal objects as cars, planes, and metal roofs look very cold (dark) on thermal images.
# - 


#%%
if __name__ == '__main__':

    #%% Exercise 1: 
    # burning wood
    # mostly radiates IR (== heat)
    # but also a little VIS

    t_wood_burning = 273 + 900                                      # [K]
    irrad = black_body_irradiance(t_wood_burning)                   # 107000 [W/m²]
    lambd = black_body_most_intense_wavelength(t_wood_burning)      # 2.4e-6 m 
    assert(lambda_ir_start > lambd > lambda_ir_end)                 # max wave is in IR

    radVisStart = black_body_radiance(lambda_vis_start, t_wood_burning)  # 145 [W/m³]
    radVisEnd   = black_body_radiance(lambda_vis_end,   t_wood_burning)  # 39 MIO [W/m³]
    visRange = lambda_vis_start - lambda_vis_end
    radRange = radVisEnd - radVisStart
    irradVis = np.pi * (radVisStart * visRange + 0.5 * visRange * radRange)  # poor man's integration
    assert(irradVis < irrad)



    # %% Exercise 2:
    # Irradiance from sun 
    F_sun = 3.9e26  # [W]
    A_sun = 4 * np.pi * 7e8**2
    E_sun = F_sun / A_sun

    # Flux through sphere around sun is equal to flux through shpere around sun with radius all the way to earth
    # F_sun = F_sun_earth
    # E_earth_distance = E_sun A_sun / A_earth_distance
    A_earth_distance = 4 * np.pi * 1.5e11**2
    E_earth = F_sun / A_earth_distance

    # That's only 0.002% of the irradiance directly on the sun's surface.

    # %%
