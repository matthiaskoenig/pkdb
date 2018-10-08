<template>
    <span id="references">
        <get-paginated-data :resource_url="resource_url">
            <div slot-scope="data">
                <references-table :data="data" :resource_url="resource_url" />
            </div>
        </get-paginated-data>
    </span>
</template>

<script>
    import GetPaginatedData from './api/GetPaginatedData';
    import ReferencesTable from './tables/ReferencesTable';

    export default {
        name: 'References',
        components: {
            GetPaginatedData: GetPaginatedData,
            ReferencesTable: ReferencesTable,

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
                return this.api + '/references_read/?format=json';
            },
        }
    }
</script>

<style></style>