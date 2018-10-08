<template>
    <get-paginated-data :resource_url="resource_url" >
        <div slot-scope="data">
            <outputs-table :data="data"  :resource_url="resource_url" />
        </div>
    </get-paginated-data>
</template>

<script>
    import GetPaginatedData from './api/GetPaginatedData';
    import OutputsTable from './tables/OutputsTable';

    export default {
        name: 'Outputs',
        components: {
            GetPaginatedData: GetPaginatedData,
            OutputsTable: OutputsTable,
        },

        computed: {
            api() {return this.$store.state.endpoints.api},

            resource_url() {
                return this.api + '/outputs_read/?format=json&final=True';
            },
        }
    }
</script>
<style>

</style>