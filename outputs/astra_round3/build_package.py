from pathlib import Path
import re, json, shutil, hashlib, zipfile

out=Path(__file__).resolve().parent
preamble=r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[a4paper,margin=25mm]{geometry}
\usepackage{amsmath,amssymb,amsthm,mathtools}
\usepackage{booktabs,longtable,array}
\usepackage[unicode,hidelinks]{hyperref}
\usepackage{microtype}
\newcommand{\E}{\mathbb E}
\newcommand{\Pbb}{\mathbb P}
\newcommand{\TV}{\operatorname{TV}}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{corollary}[theorem]{Corollary}
\theoremstyle{definition}
\newtheorem{counterexample}[theorem]{Counterexample}
\newtheorem{definition}[theorem]{Definition}
\theoremstyle{remark}
\newtheorem{remark}[theorem]{Remark}
\setlength{\emergencystretch}{3em}
\allowdisplaybreaks
\title{Round 3: Theorem and Proof Appendix\\
Decision-Relevant Uncertainty for Deterministic Boundary Learning}
\author{Research synthesis for Burak's MSc thesis}
\date{5 October 2026}
\begin{document}
\maketitle
\begin{abstract}
This standalone appendix proves the finite-pool, latent-observation,
model-perturbation, sequential, physics-transfer, discovery and geometric
statements used in the Round 3 report. It distinguishes a coherent
Bayesian experiment from an approximate refitting algorithm, and a
deterministic physical sign from a stochastic working likelihood.
PROVED means valid under the stated mathematical assumptions; it is not
a claim of research priority or an empirical result about SPH.
COUNTEREXAMPLE identifies an explicit failure of a proposed implication.
KNOWN/PRIOR ART identifies established principles or specializations.
\end{abstract}
\tableofcontents
\clearpage
\section*{Assumptions and relation to the previous rounds}
\addcontentsline{toc}{section}{Assumptions and relation to the previous rounds}
\paragraph{Fixed decision contract [KNOWN/PRIOR ART].}
Targets, candidate queries, loss and admissible actions are fixed when
comparing current and expected future risks. Binary variables are spins
in $\{-1,+1\}$ unless a construction explicitly uses bits in $\{0,1\}$.
Hamming weights are nonnegative and sum to one except where unit weights
are explicitly used; a common positive normalization does not change
competitive ratios. Conditioning is exact under the declared joint law
unless a result explicitly concerns an approximate updater. Expectations
over latent worlds and over observation noise must not be conflated.
\paragraph{Observation contract [PROVED definitions].}
A deterministic observation reveals the target sign. A logistic/probit
observation draws a Bernoulli label conditional on the latent field.
These define different experiments even when their current predictive
class probabilities happen to coincide. A stochastic working likelihood
does not establish physical randomness of a deterministic simulator.
\paragraph{Scope of inherited results [KNOWN/PRIOR ART within this project].}
The earlier $B/N$ sequential margin bound and the sharp $4/5$ result for
$N=3,B=2$ remain restricted to ideal updating, noiseless revelation,
equal-weight full-pool Hamming loss and the fixed original pool.
They are not claimed for geometric losses or the sensor examples below.
Their full proofs and rational certificates are in the accompanying
Round 1--2 reference appendix and original verification package.
The new common-sign-noise theorem below includes the one-step noiseless
$1/(N-1)$ theorem as its $\alpha=1$ case.
\paragraph{Geometry and transfer [PROVED definitions].}
Graph and normal-tube results state their coverage, derivative,
density and topology assumptions explicitly. Shrinkage results use an
exact normal-location experiment and a declared shift class, not an
unstated normal approximation to binary GP training.
\paragraph{Priority [KNOWN/PRIOR ART].}
Bayes risk reduction, SUR, Gaussian conditioning, simulation bounds,
adaptive-submodular greedy guarantees and normal-mean shrinkage have
substantial prior literature. The separate literature-priority table
identifies the closest sources and leaves priority of specific finite
constructions unresolved. No novelty follows from a bounded search.
"""
parts=[]
for name in ['latent_proofs.tex','sequential_proofs.tex','geometry_proofs.tex','synthesis_proofs.tex']:
    text=(out/name).read_text(encoding='utf-8-sig')
    def tag(m):
        env,title=m.group(1),m.group(2)
        if not any(x in title for x in ['PROVED','COUNTEREXAMPLE','KNOWN/PRIOR ART']):
            title=('COUNTEREXAMPLE; PROVED: ' if env=='counterexample' else 'PROVED: ')+title
        return '\\begin{'+env+'}['+title+']'
    text=re.sub(r'\\begin\{(theorem|proposition|lemma|counterexample|corollary)\}\[([^\]]*)\]',tag,text)
    text=text.replace('[KNOWN]','[KNOWN/PRIOR ART]').replace('[PRIOR ART]','[KNOWN/PRIOR ART]')
    text=text.replace('[PROPOSED]','[CONJECTURE: test proposal]')
    text=text.replace('[PROPOSED; mechanism CONJECTURE]','[CONJECTURE: proposed mechanism test]')
    text=text.replace('[KNOWN, code inspected]','[NUMERICALLY CHECKED: source audit]')
    text=text.replace('[PROVED; KNOWN]','[PROVED; KNOWN/PRIOR ART]')
    text=text.replace('[PRIOR ART; PROVED]','[KNOWN/PRIOR ART; PROVED]')
    text=text.replace('[PROVED; PRIOR ART]','[PROVED; KNOWN/PRIOR ART]')
    parts.append(text)
tex=preamble+'\n\n'.join(parts)+r"""
\section*{Verification and use}
\addcontentsline{toc}{section}{Verification and use}
\paragraph{Verification [NUMERICALLY CHECKED].}
The companion verification record checks the binary identity on 1,819
rational laws, the exact negative edge/Dice examples, the parity
example's identical initial pairs, and 2,036 ranked binary sequences.
The terminal moment bound was additionally checked on 2,000 random
joint-law pairs. These checks supplement the proofs and do not
establish that any assumption holds for a real campaign.
\paragraph{Experiment mapping [CONJECTURE: test proposals].}
Every useful result is paired with a computable statistic and falsifier
in the report's experiment table. Synthetic algebra checks, same-state
model diagnostics, and future-campaign policy comparisons are distinct
forms of evidence. No new empirical acquisition experiment was run.
\end{document}
"""
(out/'ROUND3_THEOREM_APPENDIX.tex').write_text(tex,encoding='utf-8')

report=(out/'ROUND3_RESEARCH_REPORT.md').read_text(encoding='utf-8')
report=report.replace('https://imjohnstone.su.domains/GE_08_09_17.pdf','https://mathweb.ucsd.edu/~jbradic/math281a/Johnstone.pdf')
(out/'ROUND3_RESEARCH_REPORT.md').write_text(report,encoding='utf-8')
sections=[('LITERATURE_PRIORITY.md','## 9. Literature and priority audit','## 10. Experiment'),
          ('EXPERIMENT_PREDICTIONS.md','## 10. Experiment-prediction','## 11. Explicit'),
          ('ASSUMPTIONS.md','## 11. Explicit assumptions','## 12. Counterexample'),
          ('COUNTEREXAMPLE_CATALOGUE.md','## 12. Counterexample','## 13. Unresolved'),
          ('OPEN_PROBLEMS.md','## 13. Unresolved','## 14. What'),
          ('WEEK16_CROSS_AUDIT.md','## 8. Week 16 cross-audit','## 9. Literature')]
for name,start,end in sections:
    s=report.index(start); e=report.index(end,s)
    (out/name).write_text(report[s:e].strip()+'\n',encoding='utf-8')
old=Path(r'C:\Users\ozgur\AppData\Local\Temp\codex-round2-theory-20261004\marginal_information_rounds_1_2.tex')
if old.exists():
    shutil.copyfile(old,out/'ROUNDS1_2_REFERENCE_APPENDIX.tex')

# Structural checks only; native LaTeX compilation is requested separately.
begin=re.findall(r'\\begin\{([^}]+)\}',tex)
end=re.findall(r'\\end\{([^}]+)\}',tex)
assert sorted(begin)==sorted(end)
labels=re.findall(r'\\label\{([^}]+)\}',tex)
assert len(labels)==len(set(labels)), 'duplicate labels'
refs=re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',tex)
assert set(refs)<=set(labels),set(refs)-set(labels)
assert tex.count('\\begin{document}')==tex.count('\\end{document}')==1
assert '\\input{' not in tex and '\\include{' not in tex
check={'theorem_environments':sum(begin.count(x) for x in ['theorem','proposition','lemma','counterexample','corollary']),
       'proof_environments':begin.count('proof'),'labels':len(labels),'references':len(refs),
       'report_words':len(report.split()),'tex_characters':len(tex),'standalone':True}
(out/'document_structure_checks.json').write_text(json.dumps(check,indent=2),encoding='utf-8')
print(json.dumps(check,indent=2))
