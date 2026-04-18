# Manual Family Reference Notes

These notes are the grounding layer for `manual_family_critic.py`. They are short, stable shape cues, not a style guide.

## Bellows
- Metallic expansion joints are built around one or more metal bellows with connectors at both ends.
- The bellows body is hollow and the end connectors are often flanges with bolt patterns.
- Reference:
  - https://en.wikipedia.org/wiki/Metal_expansion_joint
  - https://en.wikipedia.org/wiki/Expansion_joint

## Threaded Adapter
- Real adapters are continuous fittings with shoulders and connection ends.
- Threads should read as shallow helical surface detail on a cylinder, not floating rings.
- Reference:
  - https://www.mcmaster.com/products/adapter-pipe-fittings/

## Pipe Elbow
- Elbows are continuous direction-changing fittings, usually 90 or 45 degrees.
- Flanged elbows have flat flanges normal to the local pipe axis at each end.
- Reference:
  - https://en.wikipedia.org/wiki/Piping_and_plumbing_fitting
  - https://www.mcmaster.com/products/elbows/fitting-connection~flanged/

## Manifold Block
- Hydraulic manifolds are metal blocks with drilled flow passages connecting multiple ports.
- Port bosses and orthogonal drill directions help the part read correctly.
- Reference:
  - https://en.wikipedia.org/wiki/Hydraulic_manifold

## Cam
- A cam should show a deliberate non-circular lobe around a drive bore.
- Hub and keyway help it read as a driven machine element.

## Lathe Turned Part
- Turned parts should read as a sequence of axial shoulders, grooves, bores, and chamfers.
- Overly smooth blobs are too weak semantically; stepped diameters and reliefs help.
