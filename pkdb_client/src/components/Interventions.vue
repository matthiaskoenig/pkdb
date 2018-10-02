<template>
    <GetPaginatedData :resource_url="resource_url" >
    <div slot-scope="data">
        <InterventionsTable :data="data" :resource_url="resource_url" />
    </div>
    </GetPaginatedData>
</template>
<script>
    import GetPaginatedData from '@/components/api/GetPaginatedData';
    import InterventionsTable from '@/components/tables/InterventionsTable';

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