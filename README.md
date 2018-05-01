# PKDB - Pharmacokinetics database

Database for storing pharmacokinetics information.
This includes
- study data (publication data)
- trial design
- subjects information
- interventions
- dosing schemas
- pharmacokinetics parameters (
- timecourse data

## pharmacokinetics
Pharmacokinetics data is hereby a subclass of experimental data. 
These are the numerical values which are normally reported in publications.
The form can vary (mean, median) and also the error terms associated with the values (SD, SE, CV, Range). 
In addition the number of subjects is important as well (n), to be able to convert between different error
measurments.

