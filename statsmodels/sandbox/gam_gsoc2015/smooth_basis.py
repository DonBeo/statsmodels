# -*- coding: utf-8 -*-
"""
Created on Fri Jun  5 16:32:00 2015

@author: Luca
"""

## import usefull only for development ## 
from abc import ABCMeta, abstractmethod

########################################
import numpy as np
from patsy.state import stateful_transform
from patsy.util import have_pandas
if have_pandas:
    import pandas
       
### Obtain b splines from patsy ###

def _R_compat_quantile(x, probs):
    #return np.percentile(x, 100 * np.asarray(probs))
    probs = np.asarray(probs)
    quantiles = np.asarray([np.percentile(x, 100 * prob)
                            for prob in probs.ravel(order="C")])
    return quantiles.reshape(probs.shape, order="C")



## from patsy splines.py
def _eval_bspline_basis(x, knots, degree):
    try:
        from scipy.interpolate import splev
    except ImportError: # pragma: no cover
        raise ImportError("spline functionality requires scipy")
    # 'knots' are assumed to be already pre-processed. E.g. usually you
    # want to include duplicate copies of boundary knots; you should do
    # that *before* calling this constructor.
    knots = np.atleast_1d(np.asarray(knots, dtype=float))
    assert knots.ndim == 1
    knots.sort()
    degree = int(degree)
    x = np.atleast_1d(x)
    if x.ndim == 2 and x.shape[1] == 1:
        x = x[:, 0]
    assert x.ndim == 1
    # XX FIXME: when points fall outside of the boundaries, splev and R seem
    # to handle them differently. I don't know why yet. So until we understand
    # this and decide what to do with it, I'm going to play it safe and
    # disallow such points.
    if np.min(x) < np.min(knots) or np.max(x) > np.max(knots):
        raise NotImplementedError("some data points fall outside the "
                                  "outermost knots, and I'm not sure how "
                                  "to handle them. (Patches accepted!)")
    # Thanks to Charles Harris for explaining splev. It's not well
    # documented, but basically it computes an arbitrary b-spline basis
    # given knots and degree on some specificed points (or derivatives
    # thereof, but we don't use that functionality), and then returns some
    # linear combination of these basis functions. To get out the basis
    # functions themselves, we use linear combinations like [1, 0, 0], [0,
    # 1, 0], [0, 0, 1].
    # NB: This probably makes it rather inefficient (though I haven't checked
    # to be sure -- maybe the fortran code actually skips computing the basis
    # function for coefficients that are zero).
    # Note: the order of a spline is the same as its degree + 1.
    # Note: there are (len(knots) - order) basis functions.
    n_bases = len(knots) - (degree + 1)
    basis = np.empty((x.shape[0], n_bases), dtype=float)
    der1_basis = np.empty((x.shape[0], n_bases), dtype=float)    
    der2_basis = np.empty((x.shape[0], n_bases), dtype=float)    
    
    for i in range(n_bases):
        coefs = np.zeros((n_bases,))
        coefs[i] = 1
        basis[:, i] = splev(x, (knots, coefs, degree))
        der1_basis[:, i] = splev(x, (knots, coefs, degree), der=1)
        der2_basis[:, i] = splev(x, (knots, coefs, degree), der=2)
        

    return basis, der1_basis, der2_basis


def compute_all_knots(x, df, degree):
    order = degree + 1
    n_inner_knots = df - order
    lower_bound = np.min(x)
    upper_bound = np.max(x)
    knot_quantiles = np.linspace(0, 1, n_inner_knots + 2)[1:-1]
    inner_knots = _R_compat_quantile(x, knot_quantiles)
    all_knots = np.concatenate(([lower_bound, upper_bound] * order, inner_knots))
    return all_knots, lower_bound, upper_bound, inner_knots


def make_bsplines_basis(x, df, degree):
    ''' make a spline basis for x '''

    all_knots, _, _, _ = compute_all_knots(x, df, degree)
    basis, der_basis, der2_basis = _eval_bspline_basis(x, all_knots, degree)
    return basis, der_basis, der2_basis


# TODO: this function should be deleted
def make_poly_basis(x, degree, intercept=True):
    '''
    given a vector x returns poly=(1, x, x^2, ..., x^degree)
    and its first and second derivative
    '''

    if intercept:
        start = 0
    else:
        start = 1

    n_samples = len(x)
    basis = np.zeros(shape=(n_samples, degree+1 - start))
    der_basis = np.zeros(shape=(n_samples, degree+1 - start))
    der2_basis = np.zeros(shape=(n_samples, degree+1 - start))
    
    for i in range(start, degree+1):
        basis[:, i-start] = x**i
        der_basis[:, i-start] = i * x**(i-1)
        der2_basis[:, i-start] = i * (i-1) * x**(i-2)
        
    return basis, der_basis, der2_basis


class BS(object):
    """bs(x, df=None, knots=None, degree=3, include_intercept=False, lower_bound=None, upper_bound=None)
    Generates a B-spline basis for ``x``, allowing non-linear fits. The usual
    usage is something like::
      y ~ 1 + bs(x, 4)
    to fit ``y`` as a smooth function of ``x``, with 4 degrees of freedom
    given to the smooth.
    :arg df: The number of degrees of freedom to use for this spline. The
      return value will have this many columns. You must specify at least one
      of ``df`` and ``knots``.
    :arg knots: The interior knots to use for the spline. If unspecified, then
      equally spaced quantiles of the input data are used. You must specify at
      least one of ``df`` and ``knots``.
    :arg degree: The degree of the spline to use.
    :arg include_intercept: If ``True``, then the resulting
      spline basis will span the intercept term (i.e., the constant
      function). If ``False`` (the default) then this will not be the case,
      which is useful for avoiding overspecification in models that include
      multiple spline terms and/or an intercept term.
    :arg lower_bound: The lower exterior knot location.
    :arg upper_bound: The upper exterior knot location.
    A spline with ``degree=0`` is piecewise constant with breakpoints at each
    knot, and the default knot positions are quantiles of the input. So if you
    find yourself in the situation of wanting to quantize a continuous
    variable into ``num_bins`` equal-sized bins with a constant effect across
    each bin, you can use ``bs(x, num_bins - 1, degree=0)``. (The ``- 1`` is
    because one degree of freedom will be taken by the intercept;
    alternatively, you could leave the intercept term out of your model and
    use ``bs(x, num_bins, degree=0, include_intercept=True)``.
    A spline with ``degree=1`` is piecewise linear with breakpoints at each
    knot.
    The default is ``degree=3``, which gives a cubic b-spline.
    This is a stateful transform (for details see
    :ref:`stateful-transforms`). If ``knots``, ``lower_bound``, or
    ``upper_bound`` are not specified, they will be calculated from the data
    and then the chosen values will be remembered and re-used for prediction
    from the fitted model.
    Using this function requires scipy be installed.
    .. note:: This function is very similar to the R function of the same
      name. In cases where both return output at all (e.g., R's ``bs`` will
      raise an error if ``degree=0``, while patsy's will not), they should
      produce identical output given identical input and parameter settings.
    .. warning:: I'm not sure on what the proper handling of points outside
      the lower/upper bounds is, so for now attempting to evaluate a spline
      basis at such points produces an error. Patches gratefully accepted.
    .. versionadded:: 0.2.0
    """
    def __init__(self):
        self._tmp = {}
        self._degree = None
        self._all_knots = None

    def memorize_chunk(self, x, df=None, knots=None, degree=3,
                       include_intercept=False,
                       lower_bound=None, upper_bound=None):
        args = {"df": df,
                "knots": knots,
                "degree": degree,
                "include_intercept": include_intercept,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                }
        self._tmp["args"] = args
        # XX: check whether we need x values before saving them
        x = np.atleast_1d(x)
        if x.ndim == 2 and x.shape[1] == 1:
            x = x[:, 0]
        if x.ndim > 1:
            raise ValueError("input to 'bs' must be 1-d, "
                             "or a 2-d column vector")
        # There's no better way to compute exact quantiles than memorizing
        # all data.
        self._tmp.setdefault("xs", []).append(x)

    def memorize_finish(self):
        tmp = self._tmp
        args = tmp["args"]
        del self._tmp

        if args["degree"] < 0:
            raise ValueError("degree must be greater than 0 (not %r)"
                             % (args["degree"],))
        if int(args["degree"]) != args["degree"]:
            raise ValueError("degree must be an integer (not %r)"
                             % (self._degree,))

        # These are guaranteed to all be 1d vectors by the code above
        x = np.concatenate(tmp["xs"])
        if args["df"] is None and args["knots"] is None:
            raise ValueError("must specify either df or knots")
        order = args["degree"] + 1
        if args["df"] is not None:
            n_inner_knots = args["df"] - order
            if not args["include_intercept"]:
                n_inner_knots += 1
            if n_inner_knots < 0:
                raise ValueError("df=%r is too small for degree=%r and "
                                 "include_intercept=%r; must be >= %s"
                                 % (args["df"], args["degree"],
                                    args["include_intercept"],
                                    # We know that n_inner_knots is negative;
                                    # if df were that much larger, it would
                                    # have been zero, and things would work.
                                    args["df"] - n_inner_knots))
            if args["knots"] is not None:
                if len(args["knots"]) != n_inner_knots:
                    raise ValueError("df=%s with degree=%r implies %s knots, "
                                     "but %s knots were provided"
                                     % (args["df"], args["degree"],
                                        n_inner_knots, len(args["knots"])))
            else:
                # Need to compute inner knots
                knot_quantiles = np.linspace(0, 1, n_inner_knots + 2)[1:-1]
                inner_knots = _R_compat_quantile(x, knot_quantiles)
        if args["knots"] is not None:
            inner_knots = args["knots"]
        if args["lower_bound"] is not None:
            lower_bound = args["lower_bound"]
        else:
            lower_bound = np.min(x)
        if args["upper_bound"] is not None:
            upper_bound = args["upper_bound"]
        else:
            upper_bound = np.max(x)
        if lower_bound > upper_bound:
            raise ValueError("lower_bound > upper_bound (%r > %r)"
                             % (lower_bound, upper_bound))
        inner_knots = np.asarray(inner_knots)
        if inner_knots.ndim > 1:
            raise ValueError("knots must be 1 dimensional")
        if np.any(inner_knots < lower_bound):
            raise ValueError("some knot values (%s) fall below lower bound "
                             "(%r)"
                             % (inner_knots[inner_knots < lower_bound],
                                lower_bound))
        if np.any(inner_knots > upper_bound):
            raise ValueError("some knot values (%s) fall above upper bound "
                             "(%r)"
                             % (inner_knots[inner_knots > upper_bound],
                                upper_bound))
        all_knots = np.concatenate(([lower_bound, upper_bound] * order,
                                    inner_knots))
        all_knots.sort()

        self._degree = args["degree"]
        self._all_knots = all_knots

    def transform(self, x, df=None, knots=None, degree=3,
                  include_intercept=False,
                  lower_bound=None, upper_bound=None):
        basis = _eval_bspline_basis(x, self._all_knots, self._degree)
        if not include_intercept:
            basis = basis[:, 1:]
        if have_pandas:
            if isinstance(x, (pandas.Series, pandas.DataFrame)):
                basis = pandas.DataFrame(basis)
                basis.index = x.index
        return basis

# TODO: try to include other kinds of splines from patsy
# x = np.linspace(0, 1, 30)
# df = 10
# degree = 3
# from patsy.mgcv_cubic_splines import cc, cr, te
# all_knots, lower, upper, inner  = compute_all_knots(x, df, degree)
# result = cc(x, df=df, knots=all_knots, lower_bound=lower, upper_bound=upper, constraints=None)
#
# import matplotlib.pyplot as plt
#
# result = np.array(result)
# print(result.shape)
# plt.plot(result.T)
# plt.show()

class UnivariateGamSmoother(metaclass=ABCMeta):

    def __init__(self, x):

        self.x = x
        self.n_samples, self.k_variables = len(x), 1
        self.basis_, self.der_basis_, self.der2_basis_, self.cov_der2_ = self._smooth_basis_for_single_variable()
        self.dim_basis = self.basis_.shape[1]
        return

    @abstractmethod
    def _smooth_basis_for_single_variable(self):

        return


class UnivariatePolynomialSmoother(UnivariateGamSmoother):

    def __init__(self, x=None, degree=None):

        self.degree = degree
        super().__init__(x)

        return

    def _smooth_basis_for_single_variable(self):

        # TODO: unclear description
        """
        given a vector x returns poly=(1, x, x^2, ..., x^degree)
        and its first and second derivative
        """

        basis = np.zeros(shape=(self.n_samples, self.degree))
        der_basis = np.zeros(shape=(self.n_samples, self.degree))
        der2_basis = np.zeros(shape=(self.n_samples, self.degree))
        for i in range(self.degree):
            dg = i + 1
            basis[:, i] = self.x**dg
            der_basis[:, i] = dg * self.x**(dg-1)
            der2_basis[:, i] = dg * (dg-1) * self.x**(dg-2)

        cov_der2 = np.dot(der2_basis.T, der2_basis)

        return basis, der_basis, der2_basis, cov_der2


class UnivariateBSplines(UnivariateGamSmoother):

    def __init__(self, x, df, degree):

        self.degree = degree
        self.df = df
        super().__init__(x)

        return

    def _smooth_basis_for_single_variable(self):

        basis, der_basis, der2_basis = make_bsplines_basis(self.x, self.df,
                                                           self.degree)
        cov_der2 = np.dot(der2_basis.T, der2_basis)

        return basis, der_basis, der2_basis, cov_der2


class MultivariateGamSmoother(metaclass=ABCMeta):

    def __init__(self, x):

        self.x = x
        self.n_samples, self.k_variables = x.shape
        self.smoothers_ = self._make_smoothers_list()
        self.basis_ = np.hstack(smoother.basis_ for smoother in self.smoothers_)
        self.k_columns = self.basis_.shape[1]
        return

    @abstractmethod
    def _make_smoothers_list(self):

        return


class PolynomialSmoother(MultivariateGamSmoother):

    def __init__(self, x, degrees):

        self.degrees = degrees
        super().__init__(x)
        return

    def _make_smoothers_list(self):

        smoothers = []
        for v in range(self.k_variables):
            smoothers.append(UnivariatePolynomialSmoother(self.x[:, v], degree=self.degrees[v]))
        return smoothers


class BSplines(MultivariateGamSmoother):

    def __init__(self, x, dfs, degrees):
        self.degrees = degrees
        self.dfs = dfs
        super().__init__(x)
        return

    def _make_smoothers_list(self):
        smoothers = []
        for v in range(self.k_variables):
            smoothers.append(UnivariateBSplines(self.x[:, v], self.dfs[v], self.degrees[v]))

        return smoothers


class CubicSplines():
    """
    Cubic splines as described in the wood's book in chapter 3
    """

    def __init__(self, x, n_knots):
        self.x = x
        self.n_knots = n_knots

    def fit(self):
        self._equally_spaced_knots()
        self._splines_s()
        self._splines_x()
        return self

    def _equally_spaced_knots(self):
        x_min = self.x.min()
        x_max = self.x.max()
        self.knots = np.linspace(x_min, x_max, self.n_knots)
        return

    def _rk(self, x, z):
        p1 = ((z - 1/2)**2 - 1/12) * ((x - 1/2)**2 - 1/12) / 4
        p2 = ((np.abs(z - x) - 1/2)**4 - 1/2 * (np.abs(z - x) - 1/2)**2 + 7/240) / 24.
        return p1 - p2

    def _splines_x(self):
        n_columns = len(self.knots) + 2
        n_samples = self.x.shape[0]
        self.xs = np.ones(shape=(n_samples, n_columns))
        self.xs[:, 1] = self.x
        # for loop equivalent to outer(x, xk, fun=rk)
        for i, xi in enumerate(self.x):
            for j, xkj in enumerate(self.knots):
                s_ij = self._rk(xi, xkj)
                self.xs[i, j+2] = s_ij
        return

    def _splines_s(self):
        q = len(self.knots) + 2
        self.s = np.zeros(shape=(q, q))
        for i, x1 in enumerate(self.knots):
            for j, x2 in enumerate(self.knots):
                self.s[i+2, j+2] = self._rk(x1, x2)
        return
