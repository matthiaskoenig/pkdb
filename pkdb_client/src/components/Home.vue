<template>
    <div>
        <h1>Pharmacokinetics Database</h1>
        <div class="md-layout">
            <CountTable></CountTable>
        </div>
    </div>
</template>

<script>
    import CountTable from './statistics/CountTable'

    export default {
        name: 'Home',
        props: {
            api: String
        },
        components: {
            CountTable,
        }
    }
</script>

<style>
</style>