<template>
    <GetData :resource_url="resource_url" >
        <div slot-scope="resource">
            <OutputsTable :resource="resource"  :resource_url="resource_url" />
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