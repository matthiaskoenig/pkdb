<template>
    <GetData :resource_url="resource_url" >
    <div slot-scope="resource">
        <InterventionsTable :resource="resource" :api="api" :resource_url="resource_url" />
    </div>
    </GetData>
</template>
<script>
    import GetData from './GetPaginatedData';
    import InterventionsTable from './InterventionsTable';

    export default {
    name: 'Interventions',
    components: {
        GetData: GetData,
        InterventionsTable: InterventionsTable,
    },
    props: {
        api: String
    },

    data() {
        return {
            resource_url: this.api + '/interventions_read/?format=json&final=True',
            }
        }
}
</script>
<style>

</style>