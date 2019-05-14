
import axios from 'axios'
import {lookup_icon} from "@/icons"

var searchTableMixin = {
    data () {
        return {
            count: 0,
            entries: [],
            search:"",
            loading: true,
            pagination: {},
            rowsPerPageItems: [5, 10, 20, 50, 100],
            table_class: "elevation-1",
        }
    },
    props:{
            ids:{
                type: Array,
                default: () => []

            },
            autofocus: {
                type: Boolean,
                default: true
            }

        },
    mounted () {
        this.getData()
    },
    watch: {
        pagination: {
            handler () {
                this.getData()
            },
            deep: true
        },
        search: {
            handler () {
                this.getData();
            },
            deep: true
        },
        url: {
            handler () {
                this.getData();
            },
            deep: true
        }
    },
    computed: {
        backend(){
            return this.$store.state.django_domain;
        },
        api(){
            return this.$store.state.endpoints.api;
        },
        resource_url() {
            return this.$store.state.endpoints.api  + '/' + this.otype + '_elastic/?format=json'
        },
        url() {
            var url = this.resource_url
                + '&page='+ this.pagination.page
                + '&page_size='+ this.pagination.rowsPerPage
                + '&ordering='+ this.descending+ this.pagination.sortBy;
            if(this.search){
                url += '&search='+ this.search
            }
            if(this.ids.length > 0){
                url += '&ids=' + this.ids.join("__")
            }
            return url
        },
        descending() {
            return (this.pagination.descending ? "-" : "");
        }
    },
    methods: {
        icon(key) {
            return lookup_icon(key)
        },
        searchUpdate (newValue) {
            this.search = newValue
        },
        get_ids(array_of_obj) {
            return array_of_obj.map(i => i.pk)
        },

        getData() {
            if (localStorage.getItem('token'))
            { var headers = {Authorization :  'Token ' + localStorage.getItem('token')}}
            else {
                headers = {}
            }
            axios.get(this.url,{ headers: headers})
                .then(res => {
                    this.entries = res.data.data.data;
                    this.count = res.data.data.count;

                })
                .catch(err => {
                    console.log(err.response.data);
                })
                .finally(() => this.loading = false);
        },

    }
};

var UrlMixin = {
    methods: {group_url(pk) {
            return this.$store.state.endpoints.api  + '/groups_elastic/'+ pk +'/'
        },
        individual_url(pk) {
            return this.$store.state.endpoints.api  + '/individuals_elastic/'+ pk +'/'
        },
        output_url(pk) {
            return this.$store.state.endpoints.api  + '/outputs_elastic/'+ pk +'/'
        },
        timecourse_url(pk) {
            return this.$store.state.endpoints.api  + '/timecourses_elastic/'+ pk +'/'
        },
        timecourses_url(pks) {
            return this.$store.state.endpoints.api  + '/timecourses_elastic/?ids='+ pks.join('__')
        },
        intervention_url(pk) {
            return this.$store.state.endpoints.api  + '/interventions_elastic/'+ pk +'/'
        },
        reference_url(pk) {
            return this.$store.state.endpoints.api  + '/references_elastic/'+ pk +'/'
        },
        characterica_url(ids) {
            return this.$store.state.endpoints.api + '/characteristica_elastic/?ids=' + ids.join('__')
        },}
};
export {searchTableMixin,UrlMixin}