<template>
    <span id="references">
        <references-table />
    </span>
</template>

<script>
    import ReferencesTable from '../tables/ReferencesTable';

    export default {
        name: 'References',
        components: {
            ReferencesTable: ReferencesTable,
        },
    }
</script>

<style></style>