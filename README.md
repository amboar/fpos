Overview
========

The relevant scripts are:

* transform.py: Converts each bank's CSV export document into an intermediate
    representation (IR) suitable for further processing
* combine.py: Merges multiple IR documents into one time-ordered document
* annotate.py: Annotates an IR document with transaction types.
* visualise.py: Displays collated transactions as graphs and tables

Intermediate Representation
===========================

The intermediate representation and database format is CSV. The columns are:

Required
--------

1. Date, represented as dd/mm/yyyy
2. Amount, negative for expenses, positive for income
3. Description, a human decipherable annotation

Optional
--------

4. Category, describes the type of transaction from a finite set. Note that
    visualise.py requires this field.

Workflow
========

1. Export transaction data to Microsoft Excel CSV format, or the closes possible representation
2. Use transform.py to convert the data into the intermediate representation
3. Use combine.py to update an existing database with the newly acquired transaction information from 2.
4. Use annotate.py to tag transactions with a relevant type
5. Use visualise.py to understand expenditure.
