fpos - Financial Position

Overview
========

Analyse your CSV transaction data to visualise your income and expenditure.
The categories are based on those used by the Australian Tax Office on their
[MoneySmart website][1]. These scripts were hacked together out of laziness
when the author got fed up with manually entering his data into the site.

The relevant scripts are:

* transform.py: Converts each bank's CSV export document into an intermediate
    representation (IR) suitable for further processing
* combine.py: Merges multiple IR documents into one time-ordered document
* annotate.py: Annotates an IR document with transaction types.
* visualise.py: Displays collated transactions as graphs and tables

Example renderings from visualise.py can be found in the examples directory.

Workflow
========

1. Export transaction data to Microsoft Excel CSV format, or the closest
   possible representation
2. Use transform.py to convert the data into the intermediate representation
3. Use combine.py to update an existing database with the newly acquired
   transaction information from 2.
4. Use annotate.py to tag transactions with a relevant type
5. Use visualise.py to understand expenditure.

Dependencies
============

0. Python 3
1. Numpy
2. Scipy
3. Matplotlib

Intermediate Representation
===========================

The intermediate representation and database format is CSV. The columns are:

1. Date, represented as dd/mm/yyyy
2. Amount, negative for expenses, positive for income
3. Description, a human decipherable annotation
4. Category, describes the type of transaction from a finite set.

Note that transform.py must output IR with at least the first three columns.
combine.py will use data in the first three columns but will not strip the
fourth if present. annotate.py learns from rows containing the category to
guess at the category for rows lacking it and as such the document output by
annotate.py will have all four columns. visualise.py requires all four fields
to function.

Example IR Document
-------------------

    05/08/2013,981.24,Example description,Income
    06/08/2013,-67.88,Example description,Dining
    08/08/2013,-457.41,Example description,Commitment
    08/08/2013,-46.87,Example description,Commitment
    09/08/2013,-89.73,Example description,Transport
    09/08/2013,-59.75,Example description,Cash
    09/08/2013,-23.86,Example description,Utilities
    09/08/2013,-34.92,Example description,Health

[1] https://www.moneysmart.gov.au/ "Simple guidance you can trust"
