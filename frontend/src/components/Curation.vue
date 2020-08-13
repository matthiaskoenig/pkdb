<template>
    <div id="about">
      <!--
        <h1>Curation of pharmacokinetics data for PK-DB</h1>
        <p>
        A detailed guideline for curation of studies is provided in
        <a href="https://github.com/matthiaskoenig/pkdb_data/blob/develop/CURATION.md" target="_blank">CURATION.md</a>.
        </p>
        -->
        <info-node-table/>
    </div>
</template>

<script>
    import InfoNodeTable from "./tables/InfoNodeTable";

    export default {
        name: "Curation",
        components: {
            InfoNodeTable,

        },

    }
</script>

<style scoped>

</style>