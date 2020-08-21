# TODO
## Matthias
- [x] remove search for reference
- [x] fix urlslug issue
- [x] Fix the application display bug
- [x] Build component for InfoNode
- [x] Update info node information
- [x] Fix missing url for annotations
- [x] Create annotation & xref components
- [ ] Fix dead buttons in frontend (link to InfoNode component, https://github.com/matthiaskoenig/pkdb/issues/517)
- [ ] documentation of search (info buttons)
- [ ] Fix database statistics (better view, https://github.com/matthiaskoenig/pkdb/issues/486)
- [ ] Cleanup/reduction of all tables
- [ ] Fix landing page
- [ ] tables in tab component for results
- [ ] small values are not displayed. example: "http://0.0.0.0:8081/studies/PKDB00300". This library might help pretty print values "https://github.com/gentooboontoo/js-quantities". (Janek: I added it here not shure if I should do it.)
- [ ] search component upate in select
- [ ] How to handle excel sheets & file download

## Janek
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
- [ ] issues search
    - [ ] no nested components, select choices and measurement types;
    - [ ] display info node information for choices
    - [ ] example for filling the search component with data (Intervention: substance=midazolam; Group: homo sapiens; )
    - [x] update information on full selection (not only info button)
    - [o] selection of choices not working (not visible and not selectable easily)
    - [o] empty search should give all results, but currently the results are empty
    - [x] bug in search for form {option.label }} added
    - [x] no info node details on Individuals & Groups search
    - [ ] search form is too high/large, not visible on normal display
    - [x] many console errors on search (`TypeError: t.response is undefined)
    - [ ] add overall search field
    - [ ] timecourses not depicted in search results
    - [ ] search component is not scrollable (results & search independent)
    - [ ] table with scatter
- [ ] download button
    - [ ] download results button -> JSON PKDBdata (-> zip) 

- [x] Add datasets automatically for timecourses
- [ ] repair analysis serializer
- [x] create a hash for search queries to avoid very long urls  

# General @all
- [ ] REST API 
     - [ ] better REST documentation () 

- [ ] Logo & Name in Navigation menu
- [ ] Update studies in new format
- [ ] manuscript updates