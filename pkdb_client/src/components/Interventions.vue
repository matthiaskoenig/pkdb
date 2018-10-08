<template>
    <get-paginated-data :resource_url="resource_url" >
        <div slot-scope="data">
            <interventions-table :data="data" :resource_url="resource_url" />
        </div>
    </get-paginated-data>
</template>
<script>
    import GetPaginatedData from './api/GetPaginatedData';
    import InterventionsTable from './tables/InterventionsTable';

    export default {
    name: 'Interventions',
    components: {
        GetPaginatedData: GetPaginatedData,
        InterventionsTable: InterventionsTable,
    },
    computed: {
        api() {return this.$store.state.endpoints.api},

        resource_url() {
            return this.api + '/interventions_read/?format=json&final=True';
        }
    }
}
</script>
<style>

</style>