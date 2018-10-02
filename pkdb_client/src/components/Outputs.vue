<template>
    <GetData :resource_url="resource_url" >
        <div slot-scope="resource">
            <OutputsTable :resource="resource" :api="api" :resource_url="resource_url" />
        </div>
    </GetData>
</template>

<script>
    import GetData from '@/components/api/GetPaginatedData';
    import OutputsTable from '@/components/tables/OutputsTable';

    export default {
        name: 'Outputs',
        components: {
            GetData: GetData,
            OutputsTable: OutputsTable,
        },
        props: {
            api: String
        },
        data() {
            return {
                resource_url: this.api + '/outputs_read/?format=json&final=True',
                }
            }
    }
</script>
<style>

</style>