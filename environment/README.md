# Environment variables 

It aims to decouple the application environment configuration variables,
as well as the separation of these variables into specific scopes. 

## Filling it

Fill in the information with no commas or quotes 

## NOTES

i) Don't leave blank spaces or use quotes (double or single) because the
quotes are loaded by docker as part of the whole string variable. The
same to LISTS; they must have their values ​​separated by commas, no
spaces or quotes.  

ii) Don't leave unfilled variables (VAR =); comment it, assign it to any
value, or delete it.


iii) All variables ​​are imported by docker-compose as text, so each
program that consumes them, should convert them into the proper type.
