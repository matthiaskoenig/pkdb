"""
This examples shows how based on time and concentration vector the
pharmacokinetic parameters can be calculated.
"""
import pharmacokinetic
import pandas as pd
from matplotlib import pyplot as plt


def example1():
    """ Example for pharmacokinetics calculation.

    :return:
    """
    df = pd.read_csv("data_example1.csv", sep="\t", na_values="NA")

    # ------------------------------------------
    # Pharmacokinetic parameter for caffeine
    # ------------------------------------------
    # get caffeine data
    bodyweight = 70  # [kg]
    dose = 100  # [mg]
    substance = "caffeine"

    for tissue in df.tissue.unique():
        for group in df.group.unique():
            print("substance: {}, dose: {}".format(substance, dose))
            data = df[(df.tissue == tissue) & (df.group == group)]

            # calculate pharmacokinetic information
            t = data.time
            c = data.caf



            pk = pharmacokinetic.f_pk(
                t=t,
                c=c,
                compound=substance,
                dose=dose,
                bodyweight=bodyweight,
                t_unit="h",
                c_unit="mg/L",
                dose_unit="mg",
                vd_unit="L",
                bodyweight_unit="kg",
            )

            info = pharmacokinetic.pk_report(pk)
            print(info)
            pharmacokinetic.pk_figure(t=t, c=c, pk=pk)


def example2():
    """ Example for pharmacokinetics calculation.

    This demonstrates the extreme examples of time courses with only limited data points.
    On caffeine the regressions can be calculated, on paraxanthine this is not possible any more (only a single datapoint
    or one data point after the maximum.

    :return:
    """
    df = pd.read_csv("data_example2.csv", sep="\t", na_values="NA")

    # ------------------------------------------
    # Pharmacokinetic parameter for caffeine
    # ------------------------------------------
    # get caffeine data
    bodyweight = 70  # [kg]

    for (substance, dose_per_kg) in [
        ["caffeine", 2],
        ["caffeine", 4],
        ["paraxanthine", 2],
        ["paraxanthine", 4],
    ]:
        print("substance: {}, dose: {}".format(substance, dose_per_kg))
        data = df[(df.substance == substance) & (df.dose == dose_per_kg)]

        # calculate pharmacokinetic information
        dose = dose_per_kg * bodyweight  # [mg/kg]*[kg]=[mg]
        t = data.time
        if substance == "caffeine":
            c = data.caf
        elif substance == "paraxanthine":
            c = data.px



        pk = pharmacokinetic.f_pk(
            t=t,
            c=c,
            compound=substance,
            dose=dose,
            bodyweight=bodyweight,
            t_unit="h",
            c_unit="mg/L",
            dose_unit="mg",
            vd_unit="L",
            bodyweight_unit="kg",
        )

        info = pharmacokinetic.pk_report(pk)
        print(info)
        pharmacokinetic.pk_figure(t=t, c=c, pk=pk)
    plt.show()


if __name__ == "__main__":
    example1()
    example2()
    plt.show()
