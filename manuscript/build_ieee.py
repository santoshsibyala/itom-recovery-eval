"""Typeset the AGENT workshop manuscript using IEEE conference defaults."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'ITOM_AGENT_2027_v21.md'

def escape(s):
    s = s.replace('’', "'").replace('κ', 'kappa')
    mapping = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_\allowbreak{}', '{': r'\{', '}': r'\}'}
    return ''.join(mapping.get(c, c) for c in s).replace('×', r'$\times$')

def prose(s):
    parts = re.split(r'(\[[^\]]+\]\(https?://[^)]+\))', s)
    out = []
    for part in parts:
        m = re.fullmatch(r'\[([^\]]+)\]\((https?://[^)]+)\)', part)
        if m:
            out.append(r'\url{' + m[2] + '}' if m[1] == m[2] else r'\href{' + m[2] + '}{' + escape(m[1]) + '}')
        else:
            out.append(re.sub(r'\[(\d+)\]', lambda m: r'\cite{ref' + m[1] + '}', escape(part)))
    return ''.join(out)

def build():
    paragraphs = SOURCE.read_text().strip().split('\n\n')
    title = paragraphs[0][2:]
    tex = [r'''\documentclass[conference,10pt]{IEEEtran}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,booktabs,array,url,graphicx}
\usepackage[hidelinks]{hyperref}

\setlength{\emergencystretch}{1em}
\title{''' + escape(title) + r'''}
\author{\IEEEauthorblockN{Santosh Sibyala}\IEEEauthorblockA{ORCID: 0009-0000-5970-4166\\santoshsibyala@gmail.com}}
\begin{document}
\maketitle
''']
    i = 3
    references = False
    table_no = 0
    while i < len(paragraphs):
        p = paragraphs[i]
        if p == '## Abstract':
            tex += [r'\begin{abstract}', prose(paragraphs[i+1]), r'\end{abstract}']
            i += 2
            continue
        if p.startswith('Keywords: '):
            tex += [r'\begin{IEEEkeywords}', prose(p[10:]), r'\end{IEEEkeywords}']
        elif p == '[FIGURE_CORE_FAILURE]':
            tex += [r'\begin{figure}[!t]', r'\centering', r'\includegraphics[width=\columnwidth]{figures/core_failure.pdf}', r'\caption{Illustrative failure sequence. Passing health and a RECOVERED report do not establish preservation of concurrent operator work.}', r'\label{fig:core-failure}', r'\end{figure}']
        elif p == '## References':
            references = True
            tex += [r'\begin{thebibliography}{12}']
        elif p.startswith('## Appendix'):
            if references:
                tex += [r'\end{thebibliography}']
                references = False
            tex += [r'\appendices', r'\section{Artifact Navigation}']
        elif p in ('## Acknowledgments', '## Data and code availability'):
            tex += [r'\section*{' + escape(p[3:]) + '}']
        elif p.startswith('## '):
            tex += [r'\section{' + escape(re.sub(r'^## \d+\. ', '', p)) + '}']
        elif p.startswith('### '):
            tex += [r'\subsection{' + escape(re.sub(r'^### \d+\.\d+ ', '', p)) + '}']
        elif p.startswith('- '):
            tex += [r'\begin{itemize}']
            tex += [r'\item ' + prose(line[2:]) for line in p.splitlines() if line.startswith('- ')]
            tex += [r'\end{itemize}']
        elif p.startswith('|'):
            table_no += 1
            rows = [[c.strip() for c in line.strip('|').split('|')] for line in p.splitlines()]
            caption = re.sub(r'^Table \d+\. ', '', paragraphs[i+1])
            wide = table_no in (2,)
            env = 'table*' if wide else 'table'
            width = r'\textwidth' if wide else r'\columnwidth'
            # Model and endpoint labels retain full words; flexible columns wrap them.
            spec = ''.join(r'>{\raggedright\arraybackslash}p{\dimexpr' + width + '/' + str(len(rows[0])) + r'-6pt\relax}' for _ in rows[0])
            if table_no == 3:
                spec = ''.join(r'>{\raggedright\arraybackslash}p{\dimexpr' + f'{v}\\columnwidth-6pt' + r'\relax}' for v in (0.26, 0.06, 0.15, 0.18, 0.14, 0.21))
            if table_no in (4, 5):
                spec = r'@{}lcccc@{}'
            tex += [r'\begin{' + env + '}[!t]', r'\caption{' + prose(caption) + '}',
                    r'\label{tab:' + str(table_no) + '}', r'\centering\footnotesize',
                    r'\setlength{\tabcolsep}{3pt}', r'\renewcommand{\arraystretch}{1.12}',
                    r'\begin{tabular}{' + spec + '}', r'\toprule']
            for n, row in enumerate(rows):
                if n == 1:
                    tex += [r'\midrule']
                    continue
                tex += [' & '.join(prose(c.replace('_', ' ')) for c in row) + r' \\']
            tex += [r'\bottomrule', r'\end{tabular}', r'\end{' + env + '}']
            i += 1
        elif references:
            m = re.match(r'\[(\d+)\] (.*)', p, re.S)
            tex += [r'\bibitem{ref' + m[1] + '}' + prose(m[2])]
        else:
            content = prose(p)
            content = content.replace('Section 5.5', 'Section V-E').replace('Section 6', 'Section VI')
            content = re.sub(r'Table ([1-5])(?![0-9])', lambda m: r'Table~\ref{tab:' + m[1] + '}', content)
            content = content.replace('C = R AND P AND H AND D.', r'\begin{equation} C = R \land P \land H \land D. \end{equation}')
            content = content.replace('Operational recovery is C AND V.', r'Operational recovery is $C \land V$.')
            # Allow a long pinned source hash to break without changing its characters.
            content = content.replace('068c327ab3f9b79a86a39503946e26320b74b97a', r'\texttt{068c327a\allowbreak b3f9b79a\allowbreak 86a39503\allowbreak 946e2632\allowbreak 0b74b97a}')
            tex += [content]
        i += 1
    if references:
        tex += [r'\end{thebibliography}']
    tex += [r'\end{document}']
    (HERE / 'ITOM_AGENT_2027_v21.tex').write_text('\n\n'.join(tex) + '\n')

if __name__ == '__main__':
    build()
