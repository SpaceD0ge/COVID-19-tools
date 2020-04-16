class SEIR_HCD:
    """
    https://en.wikipedia.org/wiki/Compartmental_models_in_epidemiology
    Succeptible - Exposed - Infectious - Recovered compartmental model
    with Hospitalized - Critical - Fatal parameters by research group
    of Richard Neher.
    Links/sources:
    https://covid19-scenarios.org/about
    https://www.kaggle.com/anjum48/seir-hcd-model
    """

    def __init__(self):
        pass

    def _susceptible(self, S, I, R_t, infectious_period):
        return -(R_t / infectious_period) * I * S

    def _exposed(self, S, E, I, R_t, infectious_period, incubation_period):
        return (R_t / infectious_period) * I * S - (E / incubation_period)

    def _infected(self, I, E, incubation_period, infectious_period):
        return (E / incubation_period) - (I / infectious_period)

    def _hospitalized(
        self,
        I, C, H,
        infectious_period,
        time_in_hospital, time_critical,
        mild_fraction, fatal_fraction
    ):
        return (
            ((1 - mild_fraction) * (I / infectious_period))
            + ((1 - fatal_fraction) * C / time_critical)
            - (H / time_in_hospital)
        )

    def _critical(self, H, C, time_in_hospital, time_critical, critical_fraction):
        return (critical_fraction * H / time_in_hospital) - (C / time_critical)

    def _recovered(
        self,
        I, H,
        infectious_period,
        time_in_hospital,
        mild_fraction, critical_fraction
    ):
        return (mild_fraction * I / infectious_period) + (1 - critical_fraction) * (
            H / time_in_hospital
        )

    def _dead(self, C, time_critical, fatal_fraction):
        return fatal_fraction * C / time_critical

    def model(
        self,
        time_step, y,
        R_t,
        incubation_period=2.9, infectious_period=5.2,
        time_in_hospital=4, time_critical=14,
        mild_fraction=0.8, critical_fraction=0.1, fatal_fraction=0.3
    ):
        if callable(R_t):
            R_t = R_t(time_step)

        S, E, I, R, H, C, D = y

        S_out = self._susceptible(S, I, R_t, infectious_period)
        E_out = self._exposed(S, E, I, R_t, infectious_period, incubation_period)
        I_out = self._infected(I, E, incubation_period, infectious_period)
        R_out = self._recovered(
            I, H, infectious_period, time_in_hospital, mild_fraction, critical_fraction
        )
        H_out = self._hospitalized(
            I, C, H,
            infectious_period,
            time_in_hospital, time_critical,
            mild_fraction, fatal_fraction
        )
        C_out = self._critical(H, C, time_in_hospital, time_critical, critical_fraction)
        D_out = self._dead(C, time_critical, fatal_fraction)
        return [S_out, E_out, I_out, R_out, H_out, C_out, D_out]

    def __call__(self, *args):
        return self.model(*args)
