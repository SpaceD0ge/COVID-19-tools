from scipy.optimize import minimize, NonlinearConstraint
from sklearn.metrics import mean_squared_log_error
from scipy.integrate import solve_ivp
from .seir import SEIR_HCD
import numpy as np


DEFAULT_STATES = {
    "R_0": [3.6, (1, 4)],
    "time_incubation": [5, (2, 10)],
    "time_infectious": [2, (1.5, 16)],
    "time_in_hospital": [4, (2, 10)],
    "time_critical": [10, (1, 20)],
    "mild_fraction": [0.8, (0.6, 0.95)],
    "critical_fraction": [0.1, (0.05, 0.65)],
    "fatal_fraction": [0.2, (0.01, 0.65)],
    "k": [2, (1, 10)],
    "L": [50, (1, 200)],
}


class CompartmentalModel:
    def __init__(self, model_function, optimize_days=21):
        self.model = model_function
        self.optim_days = optimize_days

    def _get_optimization_args(self, params):
        """
        Returns parameters with the reproduction number decayed by Hill.
        Assume this order of parameters:
            (R_0, t_inc, t_inf, t_hosp, t_crit,
            mild, critical, fatal,
            k, L)
        """
        R_0 = params[0]
        k, L = params[-2:]

        def time_varying_reproduction(t):
            return R_0 / (1 + (t / L) ** k)

        args = (time_varying_reproduction,) + tuple(params[1:-2])
        return args

    def _get_predictions(self, sol, population):
        """
        Returns predictions of confirmed cases and fatalities.
        Original solution values are measured in fractions of population.
        """
        sus, exp, inf, rec, hosp, crit, deaths = sol.y
        pred_cases = np.clip(inf + rec + hosp + crit + deaths, 0, np.inf) * population
        pred_fatal = np.clip(deaths, 0, np.inf) * population
        return pred_cases, pred_fatal

    def _eval_msle(self, sol, data_cases, data_deaths, population):
        """
        Weighted mean squared log error for measuring data similarity.
        Returns combined msle score with predicted numbers.
        Used to optimize SEIR model parameters.
        """
        pred_cases, pred_fatal = self._get_predictions(sol, population)
        optim_days = min(self.optim_days, len(data_cases))
        weights = 1 / np.arange(1, optim_days + 1)[::-1]

        msle_cases = mean_squared_log_error(
            data_cases[-optim_days:], pred_cases[-optim_days:], weights
        )
        msle_fat = mean_squared_log_error(
            data_deaths[-optim_days:], pred_fatal[-optim_days:], weights
        )
        return np.mean([msle_cases, msle_fat]), (pred_cases, pred_fatal)

    def _solve_ode(self, args, population, n_infected, days):
        """
        Solve the SEIR differential equation system to get the compartmental
        function model for further optimization.
        """
        initial_state = [
            (population - n_infected) / population,
            0,
            n_infected / population,
            0,
            0,
            0,
            0,
        ]

        solution = solve_ivp(
            self.model, [0, days], initial_state, args=args, t_eval=np.arange(0, days)
        )
        return solution

    def model_optimization_function(
        self, params, data_cases, data_deaths, population, forecast_days=0
    ):
        """
        Main optimization function for comparing the SEIR model with 
        Returns either the SEIR msle likelihood score or the predicted numbers.
        """
        args = self._get_optimization_args(params)
        max_days = len(data_cases) + forecast_days
        sol = self._solve_ode(args, population, data_cases[0], max_days)
        msle_score, predicted = self._eval_msle(
            sol, data_cases, data_deaths, population
        )

        if forecast_days == 0:
            return msle_score
        return predicted


class CompartmentalOptimizer:
    """
    Compartment model interface with fit() and predict() functionality.
    Fits the SEIR model to amounts of cases and deaths.
    """

    def __init__(self, parameter_states=None, optim_days=21):
        model = CompartmentalModel(SEIR_HCD(), optim_days)
        self.model_fn = model.model_optimization_function
        self.states = parameter_states
        if parameter_states is None:
            self.states = DEFAULT_STATES
        assert list(self.states.keys()) == [
            "R_0",
            "time_incubation",
            "time_infectious",
            "time_in_hospital",
            "time_critical",
            "mild_fraction",
            "critical_fraction",
            "fatal_fraction",
            "k",
            "L",
        ]

    def fit(self, cases, deaths, population):
        initial_guess = [x[0] for x in self.states.values()]
        bounds = [x[1] for x in self.states.values()]
        cases = [int(x) for x in cases]
        deaths = [int(x) for x in deaths]

        def constraint(x):
            return x[3] - x[4]

        cons = NonlinearConstraint(constraint, 1.0, 10.0)
        result = minimize(
            self.model_fn,
            initial_guess,
            bounds=bounds,
            constraints=cons,
            args=(cases, deaths, population, False),
            method="SLSQP",
            tol=1e-10,
            options={"maxiter": 5000},
        )
        return result

    def predict(self, params, cases, deaths, population, horizon=10):
        cases = [int(x) for x in cases]
        deaths = [int(x) for x in deaths]
        predicted = self.model_fn(params, cases, deaths, population, horizon)
        return predicted
