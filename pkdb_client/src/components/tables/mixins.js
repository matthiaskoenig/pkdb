
import axios from 'axios'
import {lookup_icon} from "@/icons"

var searchTableMixin = {
    data () {
        return {
            count: 0,
            entries: [],
            loading: true,
            search: '',
            pagination: {},
            rowsPerPageItems: [5, 10, 20, 50, 100],
            table_class: "elevation-1",
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
        }
    },
    computed: {
        api(){
            return this.$store.state.endpoints.api;
        },
        resource_url() {
            return this.$store.state.endpoints.api  + '/' + this.otype + '_elastic/?format=json'
        },
        url() {
            let url = this.resource_url
                + '&page='+ this.pagination.page
                + '&page_size='+ this.pagination.rowsPerPage
                + '&ordering='+ this.descending+ this.pagination.sortBy;
            if(this.search){
                url += '&search='+ this.search
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
        ids(array_of_obj) {
            return array_of_obj.map(i => i.pk)
        },
        get_characterica_url(ids) {
            return this.$store.state.endpoints.api + '/characteristica_elastic/?ids=' + ids.join('__')
        },
        getData() {
            axios.get(this.url)
                .then(res => {
                    this.entries = res.data.data.data;
                    this.count = res.data.data.count;
                })
                .catch(err => console.log(err.response.data))
                .finally(() => this.loading = false);
        }
    }
};

export {searchTableMixin}