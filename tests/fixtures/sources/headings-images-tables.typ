= Introduction

In this report, we will write some _lorem ipsum_.

#lorem(90)


= Section heading

#lorem(15)

+ The climate
  - Temperature
  - Precipitation
+ The topography
+ The geology



== Subsection with image and figure

#image("generated-image.png", width: 50%)

#lorem(15)


#figure(
  image("generated-image.png", width: 50%),
  caption: [
    A generated image using _Google Nano Banana_ model of a winter landscape.
  ],
)



== Subsection with table

#lorem(15)

#table(
  columns: (1fr, auto, auto),
  inset: 10pt,
  align: horizon,
  table.header(
    [*Shape*], [*Volume*], [*Parameters*],
  ),
  "cylinder",
  $ pi h (D^2 - d^2) / 4 $,
  [
    $h$: height \
    $D$: outer radius \
    $d$: inner radius
  ],
  "tetrahedron",
  $ sqrt(2) / 12 a^3 $,
  [$a$: edge length]
)