<template>
    <span id="references">
        <!--
        <get-paginated-data :resource_url="resource_url">
            <div slot-scope="data">
                <references-table :data="data" :resource_url="resource_url" />
            </div>
        </get-paginated-data>
        -->
        <references-table2></references-table2>

    </span>
</template>

<script>
    import ReferencesTable2 from './tables/ReferencesTable2';

    export default {
        name: 'References',
        components: {
            ReferencesTable2: ReferencesTable2,
        },
    }
</script>

<style></style>