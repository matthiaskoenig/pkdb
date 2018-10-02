<template>
    <GetPaginatedData :resource_url="resource_url" >
        <div slot-scope="data">
            <OutputsTable :data="data"  :resource_url="resource_url" />
        </div>
    </GetPaginatedData>
</template>

<script>
    import GetPaginatedData from '@/components/api/GetPaginatedData';
    import OutputsTable from '@/components/tables/OutputsTable';

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