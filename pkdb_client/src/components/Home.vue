<template>
    <div id="home">
        <div class="row">
            <div class="col-6">
                <h1>Pharmacokinetics Database</h1>
                <CountTable></CountTable>
            </div>

            <div class="col-6">
                <About></About>
            </div>
        </div>
        <div class="row">
            <h1>Statistics</h1>
            <Statistics></Statistics>
        </div>
    </div>

</template>

<script>
    import CountTable from '@/components/statistics/CountTable'
    import About from '@/components/About'
    import Statistics from "./statistics/Statistics";

    export default {
        name: 'Home',
        components: {
            Statistics,
            CountTable,
            About
        }
    }
</script>

<style>
</style>