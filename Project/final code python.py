import numpy as np
from numpy.linalg import norm, svd
import cvxpy as cp
from typing import Tuple

def null_space(A, rtol=1e-5):
    u, s, vh = np.linalg.svd(A)
    rank = (s > rtol * s[0]).sum()
    return vh[rank:].T.copy()

def pflat(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Normalization of projective points.
    Each column is considered to be a point in homogeneous coordinates.
    Normalize so that the last coordinate becomes 1.
    
    Args:
        x: matrix where each column is a point
        
    Returns:
        y: result after normalization (in homogeneous coordinates)
        alpha: depth
    """
    if len(x.shape) == 1:
        x = x.reshape(-1, 1)
    
    a, n = x.shape
    alpha = x[a-1, :]
    y = x / alpha
    return y, alpha

def l2l2_triangulation(u, P, eps_perc=0.01, max_error=15, max_iter=300):
    """
    Perform (L2,L2) triangulation to estimate a 3D point U from its 2D projections.
    
    Parameters:
        u (np.ndarray): 2D projections in multiple images
        P (list): List of projection matrices for each image
        eps_perc (float): Allowed percentage gap for solution approximation
        max_error (float): Maximum pixel error allowed
        max_iter (int): Maximum number of iterations
    
    Returns:
        tuple: (estimated 3D point, number of iterations)
    """
    print('\n\n******** Starting (L2,L2) Triangulation Algorithm ********\n\n')
    
    nbr_images = len(P)  # Get number of images (projections)
    
    eps_diff = 0
    eps_perc = 0.1  # Adjust percentage to match calculation needs
    
    # Initialize transformed camera projection matrices
    Pt = []
    
    # Initialize camera centers
    cc = np.zeros((3, nbr_images))
    
    # Translate all image points to origin
    for i in range(nbr_images):
        Tim = np.eye(3)
        Tim[0:2, 2] = -u[:, i]
        Pt_i = np.matmul(Tim, P[i])
        Pt.append(Pt_i)
        ns = null_space(Pt_i)
        if ns.size == 0:
            print("Null space is empty for camera", i)
            return None, None
        y, alpha = pflat(ns)
        cc[:, i] = y[0:3, 0]  # Use y for the first three elements

    """"""

    # Normalize the first camera matrix
    v = Pt[0][2, 0:3].T
    u_svd, s_svd, vt_svd = svd(v.reshape(-1, 1))
    v = v.reshape(-1, 1)  # Ensure v is a column vector
    sign_term = np.sign((u_svd[:, 0:1].T @ v)[0, 0])  # Compute sign of the scalar
    RR = u_svd * sign_term  # Element-wise multiplication of u_svd by sign scalar

    t0 = cc[:, 0]
    
    # Compute relative positions
    tmp = RR.T @ (cc[:, 1:] - t0[:, np.newaxis])
    
    # Create transformation matrix
    T = np.zeros((4, 4))
    T[0:3, 0:3] = RR * np.std(tmp)
    T[0:3, 3] = t0
    T[3, 3] = 1
    
    # Scale and normalize projection matrices
    im_scale = 0
    for i in range(nbr_images):
        Pt[i] = Pt[i] @ T
        Pt[i] = Pt[i] / norm(Pt[i][2, :])
        im_scale += norm(Pt[i][0:2, :])
    im_scale = im_scale / nbr_images
    
    # Scale projection matrices
    for i in range(nbr_images):
        Pt[i][0:2, :] = Pt[i][0:2, :] / im_scale
    
    P0 = Pt[0]
    
    # Set bounds
    thr = max_error / im_scale
    y_lb = 0.1
    y_ub = 10
    rect_yl, rect_yu = l2_triangulation_bound(Pt, thr, y_lb, y_ub)
    x_lb = 0
    x_ub = 0.1
    
    # Initialize triangulation
    hh = l2_triangulation_loop(Pt, rect_yl, rect_yu, x_lb, x_ub, y_lb, y_ub)
    if hh is None:
        print("Initial optimization failed.")
        return None, None
    v_opt = np.sum(hh['res'])
    U = np.array([1, *hh['y'][0:3]])

    # Store current bounds
    rect_lb = [hh['lowerbound']]
    rect = [hh]
    
    iter_count = 1
    while iter_count <= max_iter:
        # Find rectangle with smallest lower bound
        vk = min(rect_lb)
        vk_index = np.argmin(rect_lb)
        
        # Compute approximation gap
        v_diff = v_opt - vk
        perc = (v_opt - vk) / v_opt if v_opt != 0 else 0
        
        print(f'Iter: {iter_count} Residual: {v_opt * im_scale} '
              f'Approximation gap: {perc * 100}% Regions: {len(rect)}')
        
        if v_diff < eps_diff or perc < eps_perc:
            break
            
        # Split region with largest interval
        h = rect[vk_index]
        gap = rect_yu[:, vk_index] - rect_yl[:, vk_index]
        pp = np.argmax(gap)
        
        tmp_yl = rect_yl[pp, vk_index]
        tmp_yu = rect_yu[pp, vk_index]
        
        # Alpha bisection method
        best_sol = h['lambda'][pp]
        alpha = 0.1
        
        if (best_sol - tmp_yl) / (tmp_yu - tmp_yl) < alpha:
            new_border = tmp_yl + (tmp_yu - tmp_yl) * alpha
        elif (tmp_yu - best_sol) / (tmp_yu - tmp_yl) < alpha:
            new_border = tmp_yu - (tmp_yu - tmp_yl) * alpha
        else:
            new_border = best_sol

        # Update bounds for new regions
        curr_yl1 = rect_yl[:, vk_index].copy()
        curr_yu1 = rect_yu[:, vk_index].copy()
        curr_yl2 = curr_yl1.copy()
        curr_yu2 = curr_yu1.copy()
        curr_yu1[pp] = new_border
        curr_yl2[pp] = new_border
        
        # Update rectangles
        rect_yl = np.column_stack((rect_yl[:, :vk_index], curr_yl1[:, np.newaxis], curr_yl2[:, np.newaxis], 
                                 rect_yl[:, vk_index + 1:]))
        rect_yu = np.column_stack((rect_yu[:, :vk_index], curr_yu1[:, np.newaxis], curr_yu2[:, np.newaxis], 
                                 rect_yu[:, vk_index + 1:]))
        
        # Perform triangulation on new regions
        h1 = l2_triangulation_loop(Pt, curr_yl1, curr_yu1, x_lb, x_ub, y_lb, y_ub)
        h2 = l2_triangulation_loop(Pt, curr_yl2, curr_yu2, x_lb, x_ub, y_lb, y_ub)

        if h1 is None or h2 is None:
            print("Optimization failed during iteration.")
            break
        
        # Update solution if better one is found
        v_opt1 = np.sum(h1['res'])
        v_opt2 = np.sum(h2['res'])
        
        rect = rect[:vk_index] + [h1, h2] + rect[vk_index + 1:]
        rect_lb = rect_lb[:vk_index] + [h1['lowerbound'], h2['lowerbound']] + rect_lb[vk_index + 1:]
        
        if v_opt1 < v_opt:
            v_opt = v_opt1
            U = np.array([1, *h1['y'][0:3]])
        if v_opt2 < v_opt:
            v_opt = v_opt2
            U = np.array([1, *h2['y'][0:3]])
            
        # Remove useless rectangles
        remove_indices = [i for i in range(len(rect)) if rect_lb[i] > v_opt]
        for i in sorted(remove_indices, reverse=True):
            del rect[i]
            rect_yl = np.delete(rect_yl, i, axis=1)
            rect_yu = np.delete(rect_yu, i, axis=1)
            rect_lb.pop(i)
            
        iter_count += 1
        
    # Final transformation
    U = pflat(T @ U[:, np.newaxis])[0]
    U = U[0:3].flatten()
    
    print('******** Ending (L2,L2) Triangulation Algorithm ********\n\n')
    
    return U, iter_count

def l2_triangulation_bound(Pt, thr, y_lb, y_ub):
    """
    Compute lower and upper bounds for y-coordinate of a 3D point using L2 triangulation.
    
    Parameters:
        Pt (list): List of camera projection matrices (each a 3x4 matrix)
        thr (float): Threshold for reprojection residuals
        y_lb (float): Lower bound on y-coordinate
        y_ub (float): Upper bound on y-coordinate
    
    Returns:
        tuple: (rect_yl, rect_yu) Lower and upper bounds for y-coordinate
    """
    nbr_images = len(Pt)  # Number of camera views
    P0 = Pt[0]  # First camera matrix

    # Number of bounds to compute (up to 3 views)
    n = min(nbr_images - 1, 3)
    rect_yl = np.zeros(n)
    rect_yu = np.zeros(n)

    for ii in range(n):
        Ptmp = Pt[ii + 1]
        # Set up variables for cvxpy
        x = cp.Variable(2 + nbr_images)
        constraints = []

        # First residual (first camera view)
        constraints.append(cp.SOC(thr, P0[0:2, 1:4] @ x[0:3] - P0[0:2, 0]))

        # Second residual and remaining cameras
        for cnt in range(nbr_images - 1):
            index_a = 3 + cnt  # Index for auxiliary variable a2, a3, ..., an
            Ptmp_i = Pt[cnt + 1]
            constraints.append(cp.SOC(x[index_a], Ptmp_i[0:2, 1:4] @ x[0:3] - Ptmp_i[0:2, 0]))

        # Bounds on depth
        constraints += [x[0] >= y_lb, x[0] <= y_ub]

        # Objective functions to minimize and maximize x[0]
        obj_min = cp.Minimize(x[0])
        obj_max = cp.Maximize(x[0])

        # Solve for lower bound
        prob_min = cp.Problem(obj_min, constraints)
        try:
            prob_min.solve(solver=cp.SCS)
            rect_yl[ii] = prob_min.value
        except:
            rect_yl[ii] = y_lb

        # Solve for upper bound
        prob_max = cp.Problem(obj_max, constraints)
        try:
            prob_max.solve(solver=cp.SCS)
            rect_yu[ii] = prob_max.value
        except:
            rect_yu[ii] = y_ub

    return rect_yl.reshape(-1, 1), rect_yu.reshape(-1, 1)

def l2_triangulation_loop(Pt, rect_yL, rect_yU, xL, xU, yLB, yUB, verbose=False):
    nbrimages = len(Pt)
    P0 = Pt[0]

    vars = 3 + nbrimages + 3 * (nbrimages - 1)
    index_z = [3 + nbrimages + i for i in range(0, 3 * (nbrimages - 1), 3)]

    x = cp.Variable(vars)
    constraints = []
    objective = 0
    
    # First residual with relaxed cone constraint
    constraints.append(cp.SOC(x[3], P0[0:2, 1:4] @ x[0:3] - P0[0:2, 0]))

    # Process remaining residuals
    for cnt in range(nbrimages - 1):
        index = index_z[cnt]  # envelope variables start index
        indexa = 4 + cnt      # auxiliary variable index

        Ptmp = Pt[cnt + 1]    # camera cnt+1

        # Cone constraint with added slack
        slack = cp.Variable(1)
        constraints.append(cp.SOC(x[indexa] + slack, Ptmp[0:2, 1:4] @ x[0:3] - Ptmp[0:2, 0]))
        constraints.append(slack >= 0)  # Ensure non-negative slack
        objective += x[index] + 0.01 * slack  # Penalize slack slightly

        # Depth bounds with some flexibility
        yL = max(rect_yL[cnt], yLB) if cnt < len(rect_yL) else yLB
        yU = min(rect_yU[cnt], yUB) if cnt < len(rect_yU) else yUB

        # Add depth constraints with soft boundaries
        depth = Ptmp[2, 1:4] @ x[0:3] + Ptmp[2, 0]
        depth_slack = cp.Variable(1)
        constraints += [
            depth >= yL - depth_slack,
            depth <= yU + depth_slack,
            depth_slack >= 0
        ]
        objective += 0.1 * depth_slack  # Penalize depth constraint violations

        # Convex envelope constraints with relaxation
        constraints.append(x[index] >= x[indexa])
        constraints.append(x[index] >= -x[indexa])

    # Define the problem with modified objective
    prob = cp.Problem(cp.Minimize(objective), constraints)

    # Solve the problem with additional solver settings
    prob.solve(
        solver=cp.SCS,
        verbose=verbose,
        max_iters=300,   # Increase max iterations
        eps=1e-3          # Adjust solver precision
    )

    if prob.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
        U = np.concatenate(([1], x.value[0:3]))
        res = np.zeros(nbrimages)
        for ii in range(nbrimages):
            tmp, _ = pflat(Pt[ii] @ U)
            res[ii] = np.sum(tmp[0:2]**2)

        lowerbound = prob.value

        return {
            'res': res,
            'lowerbound': lowerbound,
            'y': x.value,
            'lambda': [Ptmp[2, :] @ U for Ptmp in Pt[1:]]
        }
    else:
        #if verbose:
        #    print(f"Optimization problem status: {prob.status}")
        return None

# Noisy observations
u = np.array([
    [-0.3487, -0.2224, -0.1640],
    [0.5565, 0.3505, 0.2561]
])

# Ground truth without noise
U0 = np.array([0.6084, -0.9552, 0.2676])

# Define projection matrices as a list of numpy arrays
P = []
P.append(np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 2]
]))

P.append(np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 3]
]))

P.append(np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 4]
]))

# Parameters
epsilon = 0.1
delta = 1
maxiter = 300

# Run triangulation
Ul2l2, iter_count = l2l2_triangulation(u, P, epsilon, delta, maxiter)

# Print results
print('Ground truth:')
print(U0)
print('\n(L2,L2) Estimate:')
print(Ul2l2)


