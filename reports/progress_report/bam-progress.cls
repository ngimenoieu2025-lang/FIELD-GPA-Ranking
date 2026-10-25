\NeedsTeXFormat{LaTeX2e}[2020/10/01]
\ProvidesClass{bam-progress}[2026/09/15 v2.0 IE BAM Machine Learning and Communication Skills Proposal template]

% ============================================================
% CLASS OPTIONS
% Choose one guidance option only:
%   annotated  - displays instructions and placeholders
%   clean      - hides instructions and placeholders
% The proposal is always single-column.
% ============================================================
\newif\ifannotated
\annotatedtrue
\DeclareOption{annotated}{\annotatedtrue}
\DeclareOption{clean}{\annotatedfalse}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ExecuteOptions{annotated}
\ProcessOptions\relax

\LoadClass[11pt,a4paper,onecolumn]{article}

% ============================================================
% TYPOGRAPHY AND PAGE LAYOUT
% ============================================================
\RequirePackage{iftex}
\ifPDFTeX
  \RequirePackage[T1]{fontenc}
\fi
\RequirePackage[english]{babel}
\RequirePackage[a4paper,left=17mm,right=17mm,top=13mm,bottom=16mm,headheight=0pt,headsep=0pt]{geometry}
\RequirePackage{microtype}
\RequirePackage{setspace}
\RequirePackage{enumitem}
\RequirePackage{xcolor}
\RequirePackage{graphicx}
\RequirePackage{booktabs}
\RequirePackage{tabularx}
\RequirePackage{array}
\RequirePackage[most]{tcolorbox}
\RequirePackage{titlesec}
\RequirePackage{fancyhdr}
\RequirePackage{xurl}
\RequirePackage[hidelinks,pdfencoding=auto,psdextra]{hyperref}
\RequirePackage{bookmark}

% ============================================================
% BAM VISUAL IDENTITY
% ============================================================
\definecolor{BAMblue}{HTML}{080886}
\definecolor{BAMgreen}{HTML}{70D700}
\definecolor{BAMlight}{HTML}{EEF3FA}
\definecolor{BAMborder}{HTML}{AAB8CE}
\definecolor{BAMgray}{HTML}{5F6670}
\definecolor{BAMwarning}{HTML}{B00020}

\setstretch{1.01}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.30em}
\setlength{\emergencystretch}{2em}
\raggedbottom
\urlstyle{same}
\setlist{itemsep=0.12em,topsep=0.25em,leftmargin=1.5em}
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000

% ============================================================
% SECTION FORMATTING
% ============================================================
\titleformat{\section}
  {\normalfont\large\bfseries\color{BAMblue}}
  {\thesection}{0.65em}{}
\titleformat{\subsection}
  {\normalfont\normalsize\bfseries}
  {\thesubsection}{0.60em}{}
\titlespacing*{\section}{0pt}{1.3ex plus 0.3ex minus 0.2ex}{0.45ex}
\titlespacing*{\subsection}{0pt}{0.85ex plus 0.2ex minus 0.1ex}{0.25ex}
\setcounter{secnumdepth}{2}

% ============================================================
% METADATA
% ============================================================
\newcommand{\BAM@title}{[Insert project title]}
\newcommand{\BAM@team}{[Insert team member names]}
\newcommand{\BAM@course}{Machine Learning \& Communication Skills}
\newcommand{\BAM@academicyear}{2026--2027}
\newcommand{\BAM@submissiondate}{11 October 2026, 23:59}
\newcommand{\BAM@logo}{ie-sst-logo.jpeg}
\newcommand{\BAM@bibstyle}{amsplain}
\newcommand{\BAM@bibfile}{references}

\newcommand{\BAMtitle}[1]{\gdef\BAM@title{#1}}
\newcommand{\BAMteam}[1]{\gdef\BAM@team{#1}}
\newcommand{\BAMcourse}[1]{\gdef\BAM@course{#1}}
\newcommand{\BAMacademicyear}[1]{\gdef\BAM@academicyear{#1}}
\newcommand{\BAMsubmissiondate}[1]{\gdef\BAM@submissiondate{#1}}
\newcommand{\BAMlogo}[1]{\gdef\BAM@logo{#1}}
\newcommand{\BAMbibliographystyle}[1]{\gdef\BAM@bibstyle{#1}}
\newcommand{\BAMbibliographyfile}[1]{\gdef\BAM@bibfile{#1}}

% ============================================================
% ANNOTATIONS AND PLACEHOLDERS
% Body text, annotations, and placeholders all use the document's
% normal 10 pt size. Only section headings and the proposal header
% intentionally use a different size.
% ============================================================
\newtcolorbox{BAMannotationbox}{
  enhanced,
  breakable,
  colback=BAMlight,
  colframe=BAMborder,
  boxrule=0.45pt,
  arc=1.2pt,
  left=4pt,right=4pt,top=3pt,bottom=3pt,
  before skip=3pt,after skip=4pt,
  fontupper=\normalfont\normalsize
}

\newcommand{\annotation}[1]{%
  \ifannotated
    \begin{BAMannotationbox}#1\end{BAMannotationbox}%
  \fi
}

\newcommand{\placeholder}[1]{%
  \ifannotated
    {\normalfont\normalsize\color{BAMgray}\itshape #1}%
  \fi
}

\newcommand{\BAMannotationnotice}{%
  \ifannotated
    \begin{tcolorbox}[
      enhanced,
      colback=BAMlight,
      colframe=BAMgreen,
      boxrule=0.65pt,
      arc=1.2pt,
      left=5pt,right=5pt,top=3pt,bottom=3pt,
      before skip=2pt,after skip=5pt,
      fontupper=\normalfont\normalsize
    ]
      \centering\bfseries
      ANNOTATED GUIDANCE COPY. \\ {\color{red} Change \texttt{annotated} to \texttt{clean} before preparing the submitted proposal.}
    \end{tcolorbox}
  \fi
}

% ============================================================
% PAGE STYLE
% No running header text; page numbers only.
% ============================================================
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\fancypagestyle{plain}{%
  \fancyhf{}
  \fancyfoot[C]{\thepage}
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0pt}
}

% ============================================================
% COMPACT PROPOSAL HEADER - NOT A COVER PAGE
% ============================================================
\newcommand{\makeproposalheader}{%
  \thispagestyle{plain}%
  \noindent
  \begin{minipage}[t]{0.80\linewidth}
    {\fontsize{9}{10.5}\selectfont\bfseries IE UNIVERSITY | SCHOOL OF SCIENCE \& TECHNOLOGY\par}
    \vspace{0.25em}
    {\large\bfseries\color{BAMblue} Machine Learning \& Communication Skills -- Progress Report\par}
    \vspace{0.25em}
    {\Large\bfseries \BAM@title\par}
  \end{minipage}\hfill
  \begin{minipage}[t]{0.16\linewidth}
    \raggedleft
    \IfFileExists{\BAM@logo}{\includegraphics[height=2.00cm]{\BAM@logo}}{}
  \end{minipage}
  \vspace{0.35em}

  \renewcommand{\arraystretch}{1.05}
  \begin{tabularx}{\linewidth}{@{}>{\bfseries}lX@{}}
    Team: & \BAM@team \\
    Course: & \BAM@course \\
    Academic year: & \BAM@academicyear \\
    Submission deadline: & \BAM@submissiondate \\
    Text limit: & 2 pages \\
  \end{tabularx}
  \par\vspace{0.25em}\hrule\vspace{0.35em}
}

% ============================================================
% BIBLIOGRAPHY
% ============================================================
\renewcommand{\refname}{References}
\newcommand{\BAMprintbibliography}{%
  \bibliographystyle{\BAM@bibstyle}
  \bibliography{\BAM@bibfile}
}

\AtBeginDocument{%
  \hypersetup{
    pdftitle={\BAM@title -- Machine Learning and Communication Skills Progress Report},
    pdfauthor={\BAM@team},
    pdfsubject={Machine Learning and Communication Skills Progress Report for the Bachelor in Applied Mathematics at IE University},
    pdfcreator={LaTeX with the bam-proposal class}
  }%
}

\endinput

