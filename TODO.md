# TODO
## Matthias
- [x] remove search for reference
- [x] fix urlslug issue
- [x] Fix the application display bug
- [x] Build component for InfoNode
- [x] Update info node information
- [x] Fix missing url for annotations
- [x] Create annotation & xref components
- [x] Fix database statistics (better view, https://github.com/matthiaskoenig/pkdb/issues/486)
- [x] Fix landing page
- [x] tables in tab component for results
- [ ] Cleanup/reduction of all tables
- [ ] Cleanup Study Detail view
- [ ] Fix dead buttons in frontend (link to InfoNode component, https://github.com/matthiaskoenig/pkdb/issues/517)
- [ ] documentation of search (info buttons)
- [ ] small values are not displayed. example: "http://0.0.0.0:8081/studies/PKDB00300". This library might help pretty print values "https://github.com/gentooboontoo/js-quantities". (Janek: I added it here not shure if I should do it.)
- [ ] fix study and reference link button
- [ ] Substance missing in output table

## Janek
- [ ] Search
    - [ ] Fix: search selection must be cleared before applying search examples (if things are 
    already selected in other fields examples are not working)
    - [ ] Fix: select study options are all uppercase
    - [ ] Fix: align groups and individuals button next to each other (to save space)
    - [ ] Fix: add filter for outputs/timecourses analoque to groups/individuals
    - [ ] selection of single study is not working (example1 of help)
    - [ ] why do I get timecourses in search example 2 and 3 (i.e. selection half-life or AUC as output,
    but timecourse results are given)
- [ ] REST API 
     - [ ] better REST documentation ()

- [x] replace url_slug with sid
- [x] fixed bug in frontend (loading property).
- [x] use label for 'name' in info node serializer
- [x] Fix 404 reference links;
- [x] Update studies serializer to include reference information
- [x] Search frontend: display information count (high level overview of results)
- [x] Show study & info node information on search hover
- [x] fix the group & individual checkbox behavior (concise view)
- [x] fix mistake on pkdata calucalation related to 0 outputs.
- [x] remove abstract info nodes from search
- [x] add validation on label column (only "col==" allowed) 
- [x] fix search highlight (simple solution to apply to components without need fro explicitly stating highlight)
- [x] Fix table sorting! This is currently not working, so remove sorting on all tables or fix the sorting behavior
- [x] Calculate timecourses from database
- [x] bug in concise on curators
- [x] issues sort
- [x] issues search
    - [x] no nested components, select choices and measurement types;
    - [ ] display info node information for choices
    - [x] example for filling the search component with data (Intervention: substance=midazolam; Group: homo sapiens; )
    - [x] update information on full selection (not only info button)
    - [x] selection of choices not working (not visible and not selectable easily)
    - [x] empty search should give all results, but currently the results are empty
    - [x] bug in search for form {option.label }} added
    - [x] no info node details on Individuals & Groups search
    - [x] search form is too high/large, not visible on normal display
    - [x] many console errors on search (`TypeError: t.response is undefined)
    - [x] timecourses not depicted in search results
- [x] download button
    - [x] download results button -> JSON PKDBdata (-> zip) 

- [x] Add datasets automatically for timecourses
- [x] repair analysis serializer
- [x] create a hash for search queries to avoid very long urls  

# General @all
- [x] Logo & Name in Navigation menu
- [x] Update studies in new format
- [ ] manuscript updates
    -[x] add contributions of all authors