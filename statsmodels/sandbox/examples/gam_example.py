__author__ = 'Luca Puggini: <lucapuggio@gmail.com>'
__date__ = '08/07/15'


import numpy as np
import matplotlib.pyplot as plt
from statsmodels.sandbox.gam_gsoc2015.smooth_basis import UnivariateBSplines, UnivariatePolynomialSmoother, BSplines, PolynomialSmoother
from statsmodels.sandbox.gam_gsoc2015.gam import UnivariateGamPenalty, LogitGam, GLMGam, MultivariateGamPenalty
import statsmodels.api as sm
from statsmodels.sandbox.gam_gsoc2015.gam_cross_validation.gam_cross_validation import MultivariateGAMCV, MultivariateGAMCVPath
from statsmodels.sandbox.gam_gsoc2015.gam_cross_validation.cross_validators import KFold

sigmoid = np.vectorize(lambda x: 1.0/(1.0 + np.exp(-x)))



###############################################

# n = 100
#
# # make the data
# x = np.linspace(-10, 10, n)
# y = 1/(1 + np.exp(-x*x))
# mu = y.mean()
# y[y > mu] = 1
# y[y < mu] = 0
#
# # make the splines basis ##
# df = 10
# degree = 5
# x = x - x.mean()
#
# univ_bsplines = UnivariateBSplines(x, degree=degree, df=df)
#
# # train the gam logit model ##
# alphas = [0, 0.1, 1, 10]
#
# for i, alpha in enumerate(alphas):
#     plt.subplot(2, 2, i+1)
#     params0 = np.random.normal(0, 1, df)
#     gp = UnivariateGamPenalty(univ_bsplines, wts=1, alpha=alpha)
#     g = LogitGam(y, univ_bsplines.basis_, penal=gp)
#     res_g = g.fit()
#     plt.plot(x, sigmoid(np.dot(univ_bsplines.basis_, res_g.params)))
#     plt.plot(x, y, '.')
#     plt.ylim(-1, 2)
#     plt.title('alpha=' + str(alpha))
# plt.show()
#
# # %%%%%%%%%%% Logit 2 #####################
#
#
# spector_data = sm.datasets.spector.load()
# spector_data.exog = sm.add_constant(spector_data.exog)
#
# y = spector_data.endog
# X = spector_data.exog
# x = X[:, 2]
#
# x = x - x.mean()
# degree = 4
# univ_bsplines = UnivariateBSplines(x, degree=degree, df=df)
# for i, alpha in enumerate(alphas):
#     gp = UnivariateGamPenalty(univ_bsplines, alpha=alpha)
#     gam = LogitGam(y, univ_bsplines.basis_, penal = gp)
#     res_gam = gam.fit(method='nm', max_start_irls=0,
#                       disp=1, maxiter=5000, maxfun=5000)
#     plt.subplot(2, 2, i+1)
#     plt.plot(x, sigmoid(np.dot(univ_bsplines.basis_, res_gam.params)), 'o')
#     plt.plot(x, y, '.')
#     plt.title('alpha=' + str(alpha))
#     plt.ylim(-1, 2)
# plt.show()
#
#
# # GAM GLM
#
# # y is continuous
# n = 200
# x = np.linspace(-10, 10, n)
# y = x * x + np.random.normal(0, 5, n)
# y -= y.mean()
#
# x = x - x.mean()
# univ_bsplines = UnivariateBSplines(x, degree=degree, df=df)
# plt.figure()
# alphas = [0, 0.001, 0.01, 100]
# for i, alpha in enumerate(alphas):
#     plt.subplot(2, 2, i+1)
#
#     # train the model
#     gp = UnivariateGamPenalty(univ_bsplines, alpha=alpha)
#     glm_gam = GLMGam(y, univ_bsplines.basis_, penal = gp)
#     res_glm_gam = glm_gam.fit(method='nm', max_start_irls=0,
#                               disp=1, maxiter=5000, maxfun=5000)
#     plt.plot(x, np.dot(univ_bsplines.basis_, res_glm_gam.params))
#     plt.plot(x, y, '.')
#     plt.title('GLM alpha=' + str(alpha))
# plt.show()
#
#
# # %%%%%%%%%%%%%%%%%% Multivariate GAM %%%%%%%%%%%%%%%%%%%%%%%%%%%%
#
# n = 100
# x1 = np.sort(np.random.uniform(-5, 5, n))
# x2 = np.sort(np.random.uniform(0, 10, n))
# poly = x1*x1 + x2 + np.random.normal(0, 0.01, n)
# y = sigmoid(poly)
# mu = y.mean()
# yc = y.copy()
# y[y > mu] = 1
# y[y <= mu] = 0
#
# degree1 = 3
# degree2 = 4
# x = np.vstack([x1, x2]).T
# bsplines = BSplines(x, [df, df], [degree1, degree2])
# alpha = [0, 0]
#
# mgp = MultivariateGamPenalty(bsplines, alphas=alpha, wts=[1, 1])
#
# mLG = LogitGam(y, bsplines.basis_, penal=mgp)
# res_mLG = mLG.fit(maxiter=1000, tol=1e-13)
#
# # TODO: this does not work.
# # res_mLG.plot_partial()
#
# alpha = [.1, .2]
# wts = [1, 1]
#
# mgp = MultivariateGamPenalty(bsplines, wts=wts, alphas=alpha)
#
# mLG = LogitGam(y, bsplines.basis_, penal=mgp)
# res_mLG = mLG.fit(maxiter=1000, tol=1e-13)
#
# #res_mLG.plot_partial() # TODO: partial_plot is not working
#


# Multivariate GLMGam.
n = 200
x = np.zeros(shape=(n, 2))
x[:, 0] = np.linspace(-10, -5, n)
x[:, 1] = np.linspace(5, 10, n)

y = x[:, 0]**3 + x[:, 1]**2 + np.random.normal(0, 10, n)
poly = PolynomialSmoother(x, degrees=[5, 5])

gp = MultivariateGamPenalty(poly, alphas=[0, 0], wts=[1, 1])
gam = GLMGam(y, poly.basis_, penal=gp)
gam_ris = gam.fit()
#
# gam_ris.plot_partial(poly, plot_se=False)
# plt.show()
# print(gam_ris.params)
#
# plt.plot(y, '.')
# plt.plot(gam_ris.predict(poly.basis_, '.'))
# plt.show()


# Multivariate Gam CV
def cost(y1, y2):
    return np.linalg.norm(y1 - y2) / len(y2)

cv = KFold(k_folds=5, shuffle=True)
gam_cv = MultivariateGAMCV(poly, alphas=[1, 1], gam=GLMGam, cost=cost, y=y, cv=cv)
ris_gam_cv = gam_cv.fit()

print('Cross validation error=', ris_gam_cv)

# Multivariate GAM CV path

alphas = np.linspace(0, 10, 5)
gam_cv_path = MultivariateGAMCVPath(poly, alphas=[alphas, alphas], gam=GLMGam, cost=cost, y=y, cv=cv).fit()

print(gam_cv_path.alpha_cv_, gam_cv_path.cv_error_)