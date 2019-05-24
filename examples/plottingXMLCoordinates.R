# Plotting XML coordinates of MAPS data
library(ggplot2)
x_annotation = c(-0.0004771238309331238, -0.0005113995866850019, -0.00049167784163728356)
y_annotation = c(0.00024155128630809486, 0.00020798701734747738, 0.00022843971964903176)

x_tile = c(76492.58, 11107.3447, 51121.76)
y_tile = c(79269.21, 7764.188, 49512.55)

plot(x_annotation, x_tile)
plot(y_annotation, y_tile)
