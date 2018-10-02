<template>
    <div>
        <div class="md-layout-item"></div>
        <h1>Pharmacokinetics Database</h1>
        <CountTable></CountTable>
    </div>
</template>

<script>
    import CountTable from '@/components/statistics/CountTable'

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