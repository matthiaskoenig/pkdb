<template>
    <!--
    <get-paginated-data :resource_url="resource_url">
        <div slot-scope="data">
            <studies-table :data="data" :resource_url="resource_url" />
        </div>
    </get-paginated-data>
    -->
    <studies-table2></studies-table2>

</template>

<script>
    import StudiesTable2 from "./tables/StudiesTable2";


    export default {
        name: 'Studies',
        components: {
            StudiesTable2: StudiesTable2,

        },
    }
</script>

<style></style>