"""Offline reflection prompts for a missed quiz question."""

import re
import unicodedata


TOPICS = {
    "100": (
        (r"cross-sectional|longitudinal|time series", "Were the same units observed again, or was each measured on one occasion?"),
        (r"nominal|ordinal|binary|continuous|discrete|count|rounding|measurement|observations", "Can you label, rank, count, or measure the recorded values?"),
        (r"contingency|chart|plot|histogram|polygon|empirical distribution", "What would one mark on the display represent, and what would its position tell you?"),
        (r"bimodal|unimodal|skew", "Where are the peaks, and which direction does the thinner tail extend?"),
        (r"median|mode|percentile|quartile|trimmed|midrange|range", "Try ordering the values. Which positions or repeats matter for the quantity being asked for?"),
        (r"variance|deviation|coefficient", "How does the calculation use distance from the centre, and what happens to the units?"),
        (r"mean|frequency", "Which values contribute equally, and which might need to count more than once?"),
        (r"complement|exclusive|overlap|union|space", "Could both events occur on the same trial? Sketch the outcomes that each event includes."),
        (r"joint|conditional|marginal|independen|odds", "Which outcomes satisfy the event, and which outcomes belong in the denominator?"),
    ),
    "200": (
        (r"bootstrap|sampling|cluster|stratified|systematic|frame|selection bias|equal probability|sample statistic|population parameter|observed data", "What is observed once, and what would vary if the entire procedure were repeated?"),
        (r"standard error|variance of the sample mean|finite population|sample proportion", "Does the question describe variation among individual observations or variation across repeated samples?"),
        (r"central limit|clt|normal approximation|law of large|convergence|continuity correction|finite-variance|chebyshev|dependence between draws|exact normal", "Is the claim about raw observations, the centre of a statistic, or the shape of its distribution as the sample grows?"),
        (r"bernoulli|binomial|poisson|geometric|hypergeometric|multinomial", "Are you counting outcomes in a fixed set, waiting for an event, or drawing from a pool that changes after each draw?"),
        (r"uniform|chi-squared|cauchy|exponential|lognormal|gamma|beta|standard normal|student", "Which values can occur, and what feature of the shape or starting process distinguishes the choices?"),
        (r"conditional|marginal|joint|probability (mass|density|distribution)|cumulative|survival|interval probability|percentile", "Try marking the requested values on a line or in a table. Which part of the distribution are you using?"),
        (r"covariance|correlation|independence", "Would knowing the first value change what you expect for the second? What kind of association is being measured?"),
        (r"expected|mean|variance|moment|skewness|kurtosis|z-score|inequality|variable", "Which part of the calculation changes the centre, and which part changes how far values sit from it?"),
    ),
    "300": (
        (r"blinding|concealment|placebo|dummy", "Who could know which treatment was assigned, and when could they know it?"),
        (r"study|case series|allocation|blocking|carryover|crossover|factorial|interaction|pairs|per-protocol|intention-to-treat|parallel-group|recruitment|wash-out|confounding|control", "How were people grouped or assigned, and which comparisons does that design allow?"),
        (r"confidence|interval|standard error|margin of error|equal-tail|t-distribution|normal distribution", "Is the target a fixed quantity, a future observation, or a fraction of a population?"),
        (r"bonferroni|familywise", "Is the error being controlled for one comparison or for all the comparisons together?"),
        (r"statistic|critical value", "Which value serves as the benchmark, and what scale puts the observed difference in context?"),
        (r"null|alternative|critical|significance|p-value|one-sided|two-sided|test|power|false|error rate|type i|permut", "Start by assuming the claim being tested is true. Which outcomes would count as evidence against it?"),
        (r"bias|estimand|estimate|estimator|precision|effect size|odds|risk|efficiency|proportion|consistency|sufficient|jackknife|likelihood|moment|plug-in|squared error|variance", "Separate the quantity you want, the rule that estimates it, and the value obtained from this sample."),
    ),
    "400": (
        (r"leverage|influence|case deletion|cook|dfbeta|outlier|studentized|pearson residual|standardized residual", "Does the observation have unusual inputs, an unusual outcome given its inputs, or a large effect on the fit?"),
        (r"autocorrelation|residual plot|residual runs|heteroscedastic|overdispersion|poisson variability|normal probability|multicollinearity|variance inflation|robust|deviance", "Could the issue be dependence, changing spread, a different distributional shape, or overlapping information in the predictors?"),
        (r"mcnemar|cochran|matched binary|homogeneity|symmetry", "Which observations belong to the same unit, and which patterns of change contribute to the comparison?"),
        (r"contingency|frequency|fisher|chi-square|mantel|simpson|stratification|margin|within-row|risk|odds|logit|logistic|probit|poisson|ordered response", "Which group or stratum is the denominator, and is the comparison on the probability, count, or transformed scale?"),
        (r"interaction", "Would the effect of changing one input be the same at every value of the other input?"),
        (r"bonferroni", "What changes about the chance of a false alarm when several comparisons are made?"),
        (r"anova|contrast|factor|block|effect|mean square|sum of squares|covariance", "What comparisons belong to the model, and what variation provides the baseline for those comparisons?"),
        (r"regression|predictor|coefficient|correlation|least.squares|fitted|residual|intercept|extrapolat|dummy|response|origin|variance explained|explanatory", "Which quantity is being predicted, and what information is held fixed when a predictor changes?"),
    ),
    "Final Year": (
        (r"leakage|cross.validation|holdout|test set|training error|resubstitution|press|fit count|leave-one-out|deleted residual", "Which observations were available when you fit the model, and which were set aside to assess it?"),
        (r"aic|akaike|bic|bayesian information|mallows|subset|selection|elimination|parsimony|complexity|lasso|ridge|regularization|overfit|tradeoff|adjusted r", "If two models fit almost equally well, what else does the comparison reward or penalize?"),
        (r"brier|forecast scoring|prediction error|prediction|squared error", "What is the error measured for one case, and how are those errors combined?"),
        (r"missing|imput|dropout|donor|rubin|em monotonicity|expectation maximization|sensitivity|locf|nonidentification|available case|complete.case|censor|observed data|support|mean matching|mar conditional|pooled (standard error|uncertainty)|pairwise covariance", "What would you need to know about the values you cannot see, and can the observed records tell you that?"),
        (r"sample|sampling|survey|strati|census|weight|inclusion|selection|horvitz|hansen|allocation|reinterview|nonresponse|estimator|design effect|finite population|probability proportional|ratio estimation|ht relative", "How did an individual unit enter the sample, and what population should that unit represent?"),
        (r"environment|reproducib|version|dependency|provenance|artifact|codebook|workflow|script|seed|readme|metadata|execution|output|workspace|locale|parameter|portability|replication|inputs|edit|model choice|differences|literate", "What would a second analyst need to reconstruct the run from a clean starting point?"),
    ),
    "Graduate Mix": (
        (r"waic|dic|psis|stacking|log density|leave-one-group|validation|sensitivity|predictive check|discrepancy|predictive internal|predictive superiority|tail (check|mismatch)|impossible outcomes|interval coverage|assessment|mixed replication|model averag|bayes factor|bma", "What is the comparison trying to assess, and would it use observed, simulated, or held-out data?"),
        (r"pooling|shrinkage|group|random intercept|random slope|hyperprior|hyperparameter|hierarchical|exchangeab|varying effects|nested repeated|variance component", "Which parameters are shared across units, and what makes some units borrow more information than others?"),
        (r"bayes|posterior|prior|conjug|credible|loss|predictive|density parameterization|beta update", "Which quantities are fixed by the observed data, and which uncertainties are you still averaging over?"),
        (r"asymptotic|convergence|consistency|probability limit|weak law|mapping|delta|slutsky|tightness|sample size|scaling|shrinking|persistent bias|mle standard error|normal limit|centered scale|plug-in denominator|limiting variance|almost sure|vanishing excursion", "What is changing with sample size, and are you tracking a numerical limit, uncertainty, or an entire distribution?"),
        (r"likelihood|ancillary|cramer|fisher|score|information|sufficient|nuisance|wald|wilks|boundary|deviance|curvature|relative support|profile maximization|nested comparison", "Treat the observed data as fixed. Which parameters may vary, and what would you compare across their values?"),
    ),
    "AI/ML": (
        (r"leakage|validation|held.out|test set|threshold|calibration|precision|recall|accuracy|specificity|roc|false positive|false negative|true positive|true negative|harmonic mean|baseline", "Which examples make up the denominator, or which examples were available before the model was evaluated?"),
        (r"attention|position|token|retrieval|decoder|decoding|autoregressive|bigram|temperature", "When the model processes or generates this token, which information is available at that step?"),
        (r"network|backpropagation|dropout|activation|relu|gradient descent|epoch|mini batch|hidden layer|early stopping", "Is the operation changing what flows forward, how the parameters learn, or which model is kept after training?"),
        (r"search|frontier|heuristic|path cost|pruning|game|expectimax|minimax|constraint|goal|bellman|chaining|ponens|transition|markov|discount|backtracking|hill climbing|ordering", "Does the next move depend on past cost, a future estimate, a rule, or another player's choice?"),
        (r"component|scaling|centroid|clust|dbscan|linkage|silhouette|dendrogram|rand agreement|k means|unsupervised", "Are you trying to group observations, compare two partitions, or replace the original features with fewer directions?"),
        (r"supervised|classification|regression|log odds|sigmoid|tree|random forest|boosting|bagging|bootstrap aggregation|margin|kernel|support vector|naive bayes|nearest neighbo|least squares|gradient", "What form does the target take, and how does the method turn the training examples into a prediction?"),
    ),
}

CLUE_PROMPTS = {
    "definition": "Which detail in the description distinguishes two choices that seem similar?",
    "scenario": "What is being measured or compared, and which detail could rule out one of the choices?",
    "formula": "What does each part of the expression represent? Check the signs, units, and denominator.",
}
GENERAL_PROMPTS = (
    "What detail rules out your first choice?",
    "Which assumption could change the result?",
    "Where does your reasoning first diverge?",
)


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def reflection_hint(question):
    """Choose a topic prompt without repeating the answer choice verbatim."""
    concept = normalized(question.concept)
    prompts = [
        prompt for pattern, prompt in TOPICS.get(question.level, ())
        if re.search(pattern, concept)
    ]
    fallback = CLUE_PROMPTS.get(question.clue_type, GENERAL_PROMPTS[0])
    answer = re.compile(r"(?<!\w)" + re.escape(normalized(question.answer)) + r"(?!\w)")
    return next(
        prompt for prompt in (*prompts, fallback, *GENERAL_PROMPTS)
        if not answer.search(normalized(prompt))
    )
