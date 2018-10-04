<template>
    <div>
        <div id="home">
            <div class="row">
                <div class="col-md-12 col-lg-6">
                    <AboutInformation/>
                </div>

                <div class="col-md-12 col-lg-6">
                    <h2>Statistics</h2>
                    <Statistics/>
                </div>
            </div>
        </div>





    </div>
</template>

<script>
    import Statistics from '@/components/statistics/Statistics'
    import AboutInformation from "./AboutInformation";

    export default {
        name: 'About',

        components: {
            AboutInformation,
            Statistics
        },
    }
</script>

<style scoped></style>
