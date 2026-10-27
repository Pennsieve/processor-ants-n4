# Third-party software

## ANTs (Advanced Normalization Tools) 2.6.5

- Base image: `antsx/ants:2.6.5` (linux/amd64, Debian 12), https://hub.docker.com/r/antsx/ants
- Source: https://github.com/ANTsX/ANTs
- Licence: Apache License 2.0
- Tool used: `N4BiasFieldCorrection`
- Citations:
  - Tustison NJ, Avants BB, Cook PA, Zheng Y, Egan A, Yushkevich PA, Gee JC. N4ITK: improved N3 bias
    correction. IEEE Trans Med Imaging. 2010;29(6):1310-1320. https://doi.org/10.1109/TMI.2010.2046908
  - Tustison NJ, Cook PA, Holbrook AJ, et al. The ANTsX ecosystem for quantitative biological and medical
    imaging. Sci Rep. 2021;11:9068. https://doi.org/10.1038/s41598-021-87564-6

## Python packages (installed in the image)

- NiBabel 5.3.2, MIT licence, https://nipy.org/nibabel/
- NumPy 2.2.6, BSD-3-Clause licence, https://numpy.org/
- Debian `python3` 3.11 and `python3-pip`, PSF licence
