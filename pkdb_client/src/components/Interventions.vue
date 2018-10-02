<template>
    <GetData :resource_url="resource_url" >
    <div slot-scope="resource">
        <InterventionsTable :resource="resource"  :resource_url="resource_url" />
    </div>
    </GetData>
</template>
<script>
    import GetData from '@/components/api/GetPaginatedData';
    import InterventionsTable from '@/components/tables/InterventionsTable';

    export default {
    name: 'Interventions',
    components: {
        GetData: GetData,
        InterventionsTable: InterventionsTable,
    },
    computed: {
        api() {return this.$store.state.endpoints.api},

        resource_url() {
            return this.api + '/interventions_read/?format=json&final=True';
        },
    }



}
</script>
<style>

</style>