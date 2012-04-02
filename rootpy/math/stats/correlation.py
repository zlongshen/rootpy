import numpy as np
from matplotlib import pyplot as plt
from matplotlib import cm


def correlation_plot(X, weights, names, output_name, format='png'):
    """
    This function will draw an lower-triangular correlation plot

    http://stackoverflow.com/questions/2318529/plotting-only-upper-lower-triangle-of-a-heatmap
    """

    coef = np.corrcoef(X.T)
    # remove first row and last column
    coef = np.delete(coef, 0, axis=0)
    coef = np.delete(coef, -1, axis=1)

    mask =  np.tri(coef.shape[0], k=-1).T
    coef = np.ma.array(coef, mask=mask) # mask out the upper triangle
    fig = plt.figure()
    ax = fig.add_subplot(111)
    cmap = cm.get_cmap('jet', 100) # jet doesn't have white color
    cmap.set_bad('w') # default value is 'k'
    ax.imshow(coef, interpolation="nearest", cmap=cmap)
    plt.yticks(range(len(names)-1), names[1:])
    plt.xticks(range(len(names)-1), names[:-1], rotation=-30,
               rotation_mode='anchor', ha='left', va='top')
    ax.set_frame_on(False)
    ax.xaxis.set_ticks_position('none')
    ax.yaxis.set_ticks_position('none')

    for row in range(coef.shape[0]):
        for col in range(row + 1):
            plt.text(col, row, "%d%%" % (coef[row][col] * 100), ha='center', va='center')

    plt.savefig("%s.%s" % (output_name, format), bbox_inches='tight')
