# Practical Global Optimization for Multiview Geometry

## Overview
This project implements practical global optimization techniques for multiview triangulation. It involves determining the best 3D position of a point from multiple camera views, utilizing advanced optimization methods to solve complex nonlinear problems in multiview geometry.

![image](https://github.com/user-attachments/assets/e3cba127-dc24-4774-b444-bf15b2646a99)

## Features
- **Multiview Triangulation**: Recovering the 3D position of a point based on its 2D projections from multiple cameras.
- **Projective Geometry**: Techniques used to reconstruct 3D structures from 2D images.
- **Practical Global Optimization**: Branch-and-bound method with fractional programming and convex programming for scalable global optimization.
- **Convex-Concave Ratio**: Used in the optimization to minimize reprojection errors across multiple views.
- **Real-Time Requirements**: Focus on autonomous systems like drones and self-driving cars requiring real-time 3D mapping.
- **Dynamic Triangulation**: Refining bounds dynamically and using motion prediction to focus on likely regions for correct solutions.

## Objective
The goal of this project is to find the most accurate 3D position for a point in a scene using multiple camera views. This is achieved through minimizing reprojection errors and applying a practical global optimization algorithm to avoid local minima.

## Technologies
- **Branch and Bound Theory**: For systematic search space division and optimization.
- **Fractional Programming**: Minimize the sum of fractions involving the optimization of the cost function.
- **Convex Optimization**: Using tools like SeDuMi (Matlab/GNU Octave) and CVXPY for solving large-scale convex problems.
- **Kalman Filter**: For real-time tracking of dynamic points in motion (e.g., vehicles, pedestrians).

## Benefits
- **Reduced Search Space**: Focusing on likely regions based on motion prediction.
- **Higher Efficiency**: Minimizing unnecessary calculations by pruning unpromising branches.
- **Improved Accuracy**: Iterative refinement of 3D point estimates.

## Team
- **Lasitha Amarasinghe** 
- **Naindu Sirimanna** 
  
## Conclusion
This project offers a practical approach to solving the complex problem of multiview triangulation by leveraging global optimization methods. The techniques used are applicable to dynamic real-time systems like autonomous vehicles, where accurate 3D mapping is crucial for decision-making.

## Acknowledgements
This research and the development of the optimization methods are built on projective geometry principles, convex programming, and real-time computational requirements. Special thanks to the open-source optimization tools, SeDuMi and CVXPY, for their robustness in handling large-scale problems.
```
