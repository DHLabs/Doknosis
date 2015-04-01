# Doknosis

Code for the doknosis website.  Manage EO dictionary database, run
diagnostic queries.

## Compilation

- To compile static/js/doknosis.js, use the following:

    > coffee -o static/js coffeescript/doknosis.coffee

## TODO list

- Clean up server/algos.py
  - Consistency checking/removing redundant or legacy code
  - Flesh out the error handling
  - Fix algorithms currently not in use and add them back in?
  - In the greedy algorithm, it seems that the code is returning on
    the first iteration of the loop.  If this is on purpose, why the
    loop.  If not, should be fixed...

- Improve database browser

  - Could use a method of restricting browser to a particular type

  - Maybe an alphabet tab to jump around the list (paging through all
    2k entries is a pain).


## Side note

This document created by Rishi on 3/12/2015.  In creation of the
document, I'm trying to sort through the code base.  This code has
been through many iterations of authors and implementations.  As such
there are a number of coding styles and technologies represented, and
some legacy code laying around.  For now I'm not removing any of these
from the git repo because I'm not sure if their authors may want to
reference them at some point. Files not currently in use seem to be:

- fabfile.py
- server/doknosis.py
- server/calc_probabilityv12.py
- server/parseFile.py
- server/api/diseases.py
