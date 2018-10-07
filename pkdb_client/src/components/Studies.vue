<template>
    <get-paginated-data :resource_url="resource_url">
        <div slot-scope="data">
            <studies-table :data="data" :resource_url="resource_url" />
        </div>
    </get-paginated-data>
</template>

<script>
    import GetPaginatedData from './api/GetPaginatedData';
    import StudiesTable from "./tables/StudiesTable";

    export default {
        name: 'References',
        components: {
            GetPaginatedData: GetPaginatedData,
            StudiesTable: StudiesTable,

        },
        methods: {},
        data() {
            return {
            }
        },
        computed: { // vuex store
            api() {
                return this.$store.state.endpoints.api;
            },
            resource_url() {
                return this.api + '/studies_read/?format=json';
            },
        }
    }
</script>

<style></style>