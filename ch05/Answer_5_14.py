import numpy as np
import math
import matplotlib.pyplot as plt
import scipy.stats
import kernel_helper

mono = False
t_final = 12*3600

def get_lognormal(x_axis, d_mean, sigma, n_total):
    """
    Inputs
    x_axis: array of diameters (m)
    d_mean: geometric mean diameter (m)
    sigma: geometric standard deviation (1)
    n_total: total number concentration
    -------
    Output: total number concentration, units of n_total
    """
    return (n_total / (np.sqrt(2*np.pi)*np.log10(sigma))) * \
      np.exp(-(np.log10(x_axis) - np.log10(d_mean))**2 / (2*np.log10(sigma)**2))

def sample_lognormal(n_part):
    radius = np.zeros(n_part)
    num_conc = [3.2e9,2.9e9]
    log10_std_dev_radius = [.161, .217]
    char_radius = [2e-8/2,1.16e-7/2]
    counter = 0
    V = n_part / np.sum(num_conc)
    n_actual = 0
    for i_mode in range(len(char_radius)):
        n_part_mode = int(n_part * num_conc[i_mode] / np.sum(num_conc))
        x_mean_prime = np.log10(char_radius[i_mode])
        for i_part in range(n_part_mode):
            radius[counter] = 10**np.random.normal(x_mean_prime, log10_std_dev_radius[i_mode]) 
            counter +=1
        n_actual += n_part_mode
    return(radius[0:n_actual]*2, V)

def main(N_part=1000, N_bin=50, delta_t=60.0):

    rng = np.random.default_rng()
    t = 0
    diam_edges = np.logspace(-10,-5,N_bin+1)
    vol_edges = np.zeros(N_bin+1)
    for i in range(N_bin+1):
        vol_edges[i] = (1.0/6.0)*np.pi*diam_edges[i]**3

    ## Compute the max kernel values per bin pair
    MaxKernel = np.zeros((N_bin,N_bin))
    nsample = 3
    for i in range(N_bin):
        for j in range(N_bin):
            k_max = 0.0
            i_sub = np.linspace(vol_edges[i],vol_edges[i+1],nsample)
            j_sub = np.linspace(vol_edges[j],vol_edges[j+1],nsample)
            for ii in range(nsample):
                for jj in range(nsample):
                    B_sub = kernel_helper.GetKernel(i_sub[ii],j_sub[jj])
                    k_max = max(k_max, B_sub)
            MaxKernel[i,j] = k_max * 10

    # Make some initial particles
    N = np.zeros(N_bin,dtype=int)

    # Do nested list
    M = [[]]
    for i in range(N_bin):
        M.append([])

    if (mono):
        for i_part in range(N_part):
            vol = vol_edges[0] #(vol_edges[0] + vol_edges[1])*.5
            i_bin = np.where(vol >= vol_edges)[0][-1]
            M[i_bin].append(vol)
            N[i_bin] += 1
        V = N_part / 1e12
    else:
        diams, V = sample_lognormal(N_part)
        N_part = len(diams)
        for i_part in range(N_part):
            vol = diams[i_part]**3 * (np.pi/6) #(vol_edges[0] + vol_edges[1])*.5
            i_bin = np.where(vol >= vol_edges)[0][-1]
            M[i_bin].append(vol)
            N[i_bin] += 1
    print(N_part / V)
    N_init = N.copy()
    nt = int(t_final / delta_t) + 1 
    times = np.linspace(0,t_final,nt)
    total_number_conc = np.zeros(nt)
    t_index = 0
    total_number_conc[t_index] = np.sum(N) / V
    while t < t_final:
        for k in range(N_bin):
            for l in range(k+1):
                Kmax = MaxKernel[k, l]  
                if (k != l):
                    N_pairs = N[k]*N[l]
                else:
                    N_pairs = .5*N[k]*(N[l]-1)
                N_events_exact = N_pairs * Kmax / V
                N_events = np.random.poisson(N_events_exact*delta_t)
                for ll in range(N_events):
                    if (N[k] > 0 and N[l] > 0):
                        r_i = rng.integers(low=0, high=N[k]-1, size=1,endpoint=True)[0]
                        r_j = rng.integers(low=0, high=N[l]-1, size=1,endpoint=True)[0]
                        B = kernel_helper.GetKernel(M[k][r_i],M[l][r_j])
                        r = rng.random()
                        if (r < B/Kmax):
                            new_vol = M[k][r_i] + M[l][r_j]
                            dest_bin = np.where(vol_edges[k:] <= new_vol)[0][-1] + k - 1
                            M[dest_bin].append(new_vol)
                            N[dest_bin] += 1
                            if (r_i > r_j):
                                M[k].pop(r_i)
                                N[k] -= 1
                                M[l].pop(r_j)
                                N[l] -= 1     
                            else:
                                M[l].pop(r_j)
                                N[l] -= 1 
                                M[k].pop(r_i)
                                N[k] -= 1
        t += delta_t
        t_index += 1
        total_number_conc[t_index] = np.sum(N)/V
        # When the number of particles decreases too much, we will duplicate and increase volume
        if (np.sum(N) < N_part /2):
            for i_bin in range(N_bin):
                M[i_bin] = M[i_bin] + M[i_bin]
                N[i_bin] = 2* N[i_bin]
            V *= 2
       
    return (times, total_number_conc)

fig = plt.figure()
axes = fig.add_subplot(1,1,1)
n_runs = 10
tot_num_concs = []
for i_run in range(n_runs):
    (times, tot_num_conc) = main(N_part=1000)
    tot_num_concs.append(tot_num_conc)
tot_num_concs = np.array(tot_num_concs)
mean_val = np.mean(tot_num_concs,axis=0)
axes.plot(times,mean_val,label=r'$N_{\rm part} = 1000$',lw=.5)
std = np.std(tot_num_concs,axis=0)
axes.fill_between(times, mean_val-std, mean_val+std,color=axes.lines[-1].get_color(),
         alpha=.5,lw = 0)
axes.legend()
fig.tight_layout()
fig.savefig('ch05_q14a.pdf')
#axes.errorbar(times,mean_val,yerr=std)
tot_num_concs = []
for i_run in range(n_runs):
    (times, tot_num_conc) = main(N_part=10000)
    tot_num_concs.append(tot_num_conc)
tot_num_concs = np.array(tot_num_concs)
mean_val = np.mean(tot_num_concs,axis=0)
axes.plot(times,mean_val,label=r'$N_{\rm part} = 10000$',lw=.5)
std = np.std(tot_num_concs,axis=0)
axes.fill_between(times, mean_val-std, mean_val+std,color=axes.lines[-1].get_color(),
         alpha=.5,lw = 0)
#axes.errorbar(times,mean_val,yerr=std)
axes.set_xlabel('Time (s)')
axes.set_ylabel('Number concentration m$^{-3}$')
axes.set_yscale('log')
axes.legend()
fig.tight_layout()
fig.savefig('ch05_q14b.pdf')

fig = plt.figure()
axes = fig.add_subplot(1,1,1)
n_runs = 10
tot_num_concs = []
for i_run in range(n_runs):
    (times, tot_num_conc) = main(N_bin=10)
    tot_num_concs.append(tot_num_conc)
tot_num_concs = np.array(tot_num_concs)
mean_val = np.mean(tot_num_concs,axis=0)
axes.plot(times,mean_val,label=r'$N_{\rm bin} = 10$',lw=.5)
std = np.std(tot_num_concs,axis=0)
axes.fill_between(times, mean_val-std, mean_val+std,color=axes.lines[-1].get_color(),
         alpha=.5,lw = 0)
#axes.errorbar(times,mean_val,yerr=std)
tot_num_concs = []
for i_run in range(n_runs):
    (times, tot_num_conc) = main(N_bin=100)
    tot_num_concs.append(tot_num_conc)
tot_num_concs = np.array(tot_num_concs)
mean_val = np.mean(tot_num_concs,axis=0)
axes.plot(times,mean_val,label=r'$N_{\rm bin} = 100}$',lw=.5)
std = np.std(tot_num_concs,axis=0)
axes.fill_between(times, mean_val-std, mean_val+std,color=axes.lines[-1].get_color(),
         alpha=.5,lw = 0)
#axes.errorbar(times,mean_val,yerr=std)
axes.set_xlabel('Time (s)')
axes.set_ylabel('Number concentration m$^{-3}$')
axes.set_yscale('log')
axes.legend()
fig.tight_layout()
fig.savefig('ch05_q14c.pdf')
