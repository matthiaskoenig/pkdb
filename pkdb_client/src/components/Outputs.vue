<template>
    <!--
    <get-paginated-data :resource_url="resource_url" >
        <div slot-scope="data">
            <outputs-table :data="data"  :resource_url="resource_url" />
        </div>
    </get-paginated-data>

    -->
    <outputs-table2/>

</template>

<script>
    import OutputsTable2 from './tables/OutputsTable2';

    export default {
        name: 'Outputs',
        components: {
            OutputsTable2: OutputsTable2,
        },

    }
</script>
<style>

</style>