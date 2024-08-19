"""Check kernel values"""

import numpy as np
import kernel_helper

radius_particle = np.array([1e-9, 5e-7, 10e-6])  # radii in meters
mass_particle = 4 / 3 * np.pi * radius_particle**3 * 1000  # mass in kg

values = kernel_helper.GetKernel(mass_particle[2], mass_particle[2])
print(values)