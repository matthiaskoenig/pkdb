# sd is standard deviation
# se is standard error (standard deviation of the mean) sd/sqrt(n)
# cv is coeficient of variance. sd/mean
import numpy as np

def get_sd(se, count, cv, mean):
    sd = None
    is_se = sd is not None
    is_count = count is not None
    is_mean = mean is not None
    is_cv = cv is not None

    if isinstance(se, list):
        se = list(map(float, se))
    if isinstance(mean, list):
        mean = list(map(float, mean))
    if isinstance(cv, list):
        cv = list(map(float, cv))

    if is_se and is_count:
        sd = np.multiply(se, np.sqrt(count))
    elif is_cv and is_mean:
        sd = np.multiply(cv, mean)
    return sd


def get_se(sd, count, cv, mean):
    if isinstance(sd, list):
        sd = list(map(float, sd))
    if isinstance(mean, list):
        mean = list(map(float, mean))
    if isinstance(cv, list):
        cv = list(map(float, cv))

    se = None
    is_sd = sd is not None
    is_count = count is not None
    is_mean = mean is not None
    is_cv = cv is not None

    if is_sd and is_count:

        se = np.true_divide(sd, np.sqrt(count))
    elif is_count and is_mean and is_cv:
        se = np.true_divide((np.multiply(cv, mean)), np.sqrt(count))
    return se


def get_cv(sd, count, se, mean):
    if isinstance(sd, list):
        sd = list(map(float, sd))
    if isinstance(mean, list):
        mean = list(map(float, mean))
    if isinstance(se, list):
        se = list(map(float, se))

    cv = None
    is_sd = sd is not None
    is_count = count is not None
    is_mean = mean is not None
    is_se = se is not None

    if is_sd and is_mean:
        cv = np.true_divide(sd, mean)
    elif is_se and is_count and is_mean:
        cv = np.true_divide(np.multiply(se, np.sqrt(count)), mean)
    return cv
