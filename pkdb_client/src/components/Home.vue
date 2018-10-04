<template>
    <div id="home">
        <div class="row">
            <div class="col-md-12 col-lg-6">
                <CountTable></CountTable>
            </div>

            <div class="col-md-12 col-lg-6">
                <AboutInformation />
            </div>
        </div>

    </div>

</template>

<script>
    import CountTable from '@/components/statistics/CountTable'
    import AboutInformation from '@/components/AboutInformation'

    export default {
        name: 'Home',
        components: {
            CountTable,
            AboutInformation
        }
    }
</script>

<style>
</style>